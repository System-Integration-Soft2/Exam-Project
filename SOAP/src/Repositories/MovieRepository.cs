using Microsoft.Data.Sqlite;
using SoapService.Contracts.Dtos;

namespace SoapService.Repositories;

/// <summary>
/// SQLite-backed read repository for movies.
///
/// Two constructors:
///   - IConfiguration-based: used by DI in the runtime host; opens a fresh connection
///     per method call from DATABASE_PATH (scoped lifetime in DI).
///   - SqliteConnection-based: used by tests; accepts a pre-opened shared connection
///     (the :memory: fixture connection that must stay open for the test lifetime).
///
/// All queries use parameterised SqliteCommand.Parameters — no string concatenation
/// or interpolation into SQL (RISK-02).
///
/// Timestamps are read as raw strings via reader.GetString(...) — no DateTime
/// rebinding that would inject a UTC suffix (CONT-09).
/// </summary>
public class MovieRepository : IMovieRepository
{
    private readonly string? _connectionString;
    private readonly SqliteConnection? _sharedConnection;

    // DI constructor: used by the runtime host.
    public MovieRepository(IConfiguration configuration)
    {
        _connectionString = $"Data Source={configuration["DATABASE_PATH"]}";
    }

    // Test constructor: accepts a pre-opened :memory: connection.
    public MovieRepository(SqliteConnection sharedConnection)
    {
        _sharedConnection = sharedConnection;
    }

    private SqliteConnection OpenConnection()
    {
        if (_sharedConnection is not null)
            return _sharedConnection; // already open; caller must NOT dispose it

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
}
