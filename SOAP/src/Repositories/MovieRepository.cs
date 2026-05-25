using Microsoft.Data.Sqlite;
using SoapService.Contracts.Dtos;

namespace SoapService.Repositories;


// SQLite-backed repository for movies (reads + writes).

// Two constructors:
// - IConfiguration-based: used by DI in the runtime host; opens a fresh connection
// per method call from DATABASE_PATH (scoped lifetime in DI).
// - SqliteConnection-based: used by tests; accepts a pre-opened shared connection
// (the :memory: fixture connection that must stay open for the test lifetime).

// All queries use parameterised SqliteCommand.Parameters — no string concatenation
public class MovieRepository : IMovieRepository
{
    private readonly string? _connectionString;
    private readonly SqliteConnection? _sharedConnection;

    public MovieRepository(IConfiguration configuration)
    {
        _connectionString = $"Data Source={configuration["DATABASE_PATH"]}";
    }

    public MovieRepository(SqliteConnection sharedConnection)
    {
        _sharedConnection = sharedConnection;
    }

    private SqliteConnection OpenConnection()
    {
        if (_sharedConnection is not null)
            return _sharedConnection;

        var connection = new SqliteConnection(_connectionString);
        connection.Open();

        // Defensive defaults
        using var pragmaFk = connection.CreateCommand();
        pragmaFk.CommandText = "PRAGMA foreign_keys=ON";
        pragmaFk.ExecuteNonQuery();

        using var pragmaBusy = connection.CreateCommand();
        pragmaBusy.CommandText = "PRAGMA busy_timeout=5000";
        pragmaBusy.ExecuteNonQuery();

        return connection;
    }

    public IReadOnlyList<MovieDto> ListMovies()
    {
        var connection = OpenConnection();
        // Only dispose the connection if we opened it (not the shared test connection).
        var ownsConnection = _sharedConnection is null;
        try
        {
            var movies = new List<MovieDto>();

            using var cmd = connection.CreateCommand();
            cmd.CommandText =
                "SELECT id, title, director, release_year, runtime_minutes, synopsis, created_at, updated_at " +
                "FROM movies ORDER BY id";

            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                movies.Add(MapMovieRow(reader));
            }

            // N+1 genre fetch - maybe i'll optimise later with a JOIN??
            foreach (var movie in movies)
            {
                movie.Genres = FetchGenres(connection, movie.Id);
            }

            return movies;
        }
        finally
        {
            if (ownsConnection)
                connection.Dispose();
        }
    }

    public MovieDto? GetMovieById(long id)
    {
        var connection = OpenConnection();
        var ownsConnection = _sharedConnection is null;
        try
        {
            using var cmd = connection.CreateCommand();
            cmd.CommandText =
                "SELECT id, title, director, release_year, runtime_minutes, synopsis, created_at, updated_at " +
                "FROM movies WHERE id = @id";
            cmd.Parameters.AddWithValue("@id", id);

            using var reader = cmd.ExecuteReader();
            if (!reader.Read())
                return null;

            var movie = MapMovieRow(reader);
            // Close reader before running genre query on the same connection.
            reader.Close();

            movie.Genres = FetchGenres(connection, movie.Id);
            return movie;
        }
        finally
        {
            if (ownsConnection)
                connection.Dispose();
        }
    }

    private static MovieDto MapMovieRow(SqliteDataReader reader)
    {
        var directorOrdinal = reader.GetOrdinal("director");
        var runtimeOrdinal = reader.GetOrdinal("runtime_minutes");
        var synopsisOrdinal = reader.GetOrdinal("synopsis");

        return new MovieDto
        {
            Id = reader.GetInt64(reader.GetOrdinal("id")),
            Title = reader.GetString(reader.GetOrdinal("title")),
            // Director is nullable in the schema — return null when absent
            Director = reader.IsDBNull(directorOrdinal)
                ? null
                : reader.GetString(directorOrdinal),
            ReleaseYear = reader.GetInt32(reader.GetOrdinal("release_year")),
            RuntimeMinutes = reader.IsDBNull(runtimeOrdinal)
                ? null
                : reader.GetInt32(runtimeOrdinal),
            Synopsis = reader.IsDBNull(synopsisOrdinal)
                ? null
                : reader.GetString(synopsisOrdinal),
            // Timestamps read as raw strings — no DateTime rebinding
            CreatedAt = reader.GetString(reader.GetOrdinal("created_at")),
            UpdatedAt = reader.GetString(reader.GetOrdinal("updated_at")),
        };
    }

    private static List<GenreDto> FetchGenres(SqliteConnection connection, long movieId)
    {
        using var cmd = connection.CreateCommand();
        cmd.CommandText =
            "SELECT g.id, g.name " +
            "FROM genres g " +
            "INNER JOIN movie_genres mg ON g.id = mg.genre_id " +
            "WHERE mg.movie_id = @movieId " +
            "ORDER BY g.id";
        cmd.Parameters.AddWithValue("@movieId", movieId);

        var genres = new List<GenreDto>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            genres.Add(new GenreDto
            {
                Id = reader.GetInt64(reader.GetOrdinal("id")),
                Name = reader.GetString(reader.GetOrdinal("name")),
            });
        }
        return genres;
    }

    // Returns the list of genre IDs from genreIds that do not exist in the genres table.
    // Returns an empty list when all IDs are valid.
    public List<int> FindMissingGenreIds(List<int> genreIds)
    {
        var connection = OpenConnection();
        var ownsConnection = _sharedConnection is null;
        try
        {
            return FindMissingGenreIds(connection, genreIds);
        }
        finally
        {
            if (ownsConnection)
                connection.Dispose();
        }
    }

    private static List<int> FindMissingGenreIds(SqliteConnection connection, List<int> genreIds)
    {
        // Build: SELECT id FROM genres WHERE id IN (@gp0,@gp1,...)
        var placeholders = string.Join(",", genreIds.Select((_, i) => $"@gp{i}"));
        using var cmd = connection.CreateCommand();
        cmd.CommandText = $"SELECT id FROM genres WHERE id IN ({placeholders})";
        for (var i = 0; i < genreIds.Count; i++)
            cmd.Parameters.AddWithValue($"@gp{i}", genreIds[i]);

        var foundIds = new HashSet<long>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
            foundIds.Add(reader.GetInt64(0));

        return genreIds.Where(id => !foundIds.Contains(id)).ToList();
    }

    public long CreateMovie(CreateMovieRequest request)
    {
        var connection = OpenConnection();
        var ownsConnection = _sharedConnection is null;
        try
        {
            // Single explicit transaction wrapping INSERT + genre links so a mid-loop genre-insert failure cannot leave an orphaned movie row.
            using var transaction = connection.BeginTransaction();

            using var insertCmd = connection.CreateCommand();
            insertCmd.Transaction = transaction;
            insertCmd.CommandText =
                "INSERT INTO movies (title, director, release_year, runtime_minutes, synopsis, " +
                "created_at, updated_at) " +
                "VALUES (@title, @director, @releaseYear, @runtimeMinutes, @synopsis, " +
                "strftime('%Y-%m-%dT%H:%M:%S','now'), strftime('%Y-%m-%dT%H:%M:%S','now'))";
            insertCmd.Parameters.AddWithValue("@title", request.Title);
            insertCmd.Parameters.AddWithValue("@director", (object?)request.Director ?? System.DBNull.Value);
            insertCmd.Parameters.AddWithValue("@releaseYear", request.ReleaseYear);
            insertCmd.Parameters.AddWithValue("@runtimeMinutes", (object?)request.RuntimeMinutes ?? System.DBNull.Value);
            insertCmd.Parameters.AddWithValue("@synopsis", (object?)request.Synopsis ?? System.DBNull.Value);
            insertCmd.ExecuteNonQuery();

            // Retrieve the new row id inside the transaction.
            using var idCmd = connection.CreateCommand();
            idCmd.Transaction = transaction;
            idCmd.CommandText = "SELECT last_insert_rowid()";
            var newId = (long)idCmd.ExecuteScalar()!;

            // Insert genre links inside the same transaction.
            InsertGenreLinks(connection, transaction, newId, request.GenreIds);

            transaction.Commit();
            return newId;
        }
        finally
        {
            if (ownsConnection)
                connection.Dispose();
        }
    }

    public bool UpdateMovie(UpdateMovieRequest request)
    {
        var connection = OpenConnection();
        var ownsConnection = _sharedConnection is null;
        try
        {
            using var transaction = connection.BeginTransaction();

            using var updateCmd = connection.CreateCommand();
            updateCmd.Transaction = transaction;
            updateCmd.CommandText =
                "UPDATE movies SET " +
                "title = @title, " +
                "director = @director, " +
                "release_year = @releaseYear, " +
                "runtime_minutes = @runtimeMinutes, " +
                "synopsis = @synopsis, " +
                "updated_at = strftime('%Y-%m-%dT%H:%M:%S','now') " +
                "WHERE id = @id";
            updateCmd.Parameters.AddWithValue("@title", request.Title);
            updateCmd.Parameters.AddWithValue("@director", (object?)request.Director ?? System.DBNull.Value);
            updateCmd.Parameters.AddWithValue("@releaseYear", request.ReleaseYear);
            updateCmd.Parameters.AddWithValue("@runtimeMinutes", (object?)request.RuntimeMinutes ?? System.DBNull.Value);
            updateCmd.Parameters.AddWithValue("@synopsis", (object?)request.Synopsis ?? System.DBNull.Value);
            updateCmd.Parameters.AddWithValue("@id", request.Id);
            var rows = updateCmd.ExecuteNonQuery();

            if (rows == 0)
            {
                // Row does not exist — do not commit; return false for service to throw NotFoundFault
                return false;
            }

            using var deleteCmd = connection.CreateCommand();
            deleteCmd.Transaction = transaction;
            deleteCmd.CommandText = "DELETE FROM movie_genres WHERE movie_id = @movieId";
            deleteCmd.Parameters.AddWithValue("@movieId", request.Id);
            deleteCmd.ExecuteNonQuery();

            // Insert new genre links inside the same transaction.
            InsertGenreLinks(connection, transaction, request.Id, request.GenreIds);

            transaction.Commit();
            return true;
        }
        finally
        {
            if (ownsConnection)
                connection.Dispose();
        }
    }

    public bool DeleteMovie(long id)
    {
        var connection = OpenConnection();
        var ownsConnection = _sharedConnection is null;
        try
        {
            using var cmd = connection.CreateCommand();
            cmd.CommandText = "DELETE FROM movies WHERE id = @id";
            cmd.Parameters.AddWithValue("@id", id);
            var rows = cmd.ExecuteNonQuery();
            return rows > 0;
        }
        finally
        {
            if (ownsConnection)
                connection.Dispose();
        }
    }

    private static void InsertGenreLinks(
        SqliteConnection connection,
        SqliteTransaction transaction,
        long movieId,
        List<int> genreIds)
    {
        foreach (var genreId in genreIds)
        {
            using var cmd = connection.CreateCommand();
            cmd.Transaction = transaction;
            cmd.CommandText = "INSERT INTO movie_genres (movie_id, genre_id) VALUES (@movieId, @genreId)";
            cmd.Parameters.AddWithValue("@movieId", movieId);
            cmd.Parameters.AddWithValue("@genreId", genreId);
            cmd.ExecuteNonQuery();
        }
    }
}
