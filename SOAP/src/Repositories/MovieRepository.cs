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

    private async Task<SqliteConnection> OpenConnectionAsync(CancellationToken ct)
    {
        if (_sharedConnection is not null)
            return _sharedConnection; // already open; caller must NOT dispose it

        var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(ct);

        // Defensive defaults matching REST's pattern (CODE-07).
        await using var pragmaFk = connection.CreateCommand();
        pragmaFk.CommandText = "PRAGMA foreign_keys=ON";
        await pragmaFk.ExecuteNonQueryAsync(ct);

        await using var pragmaBusy = connection.CreateCommand();
        pragmaBusy.CommandText = "PRAGMA busy_timeout=5000";
        await pragmaBusy.ExecuteNonQueryAsync(ct);

        return connection;
    }

    public async Task<IReadOnlyList<MovieDto>> ListMoviesAsync(CancellationToken ct = default)
    {
        var connection = await OpenConnectionAsync(ct);
        // Only dispose the connection if we opened it (not the shared test connection).
        var ownsConnection = _sharedConnection is null;
        try
        {
            var movies = new List<MovieDto>();

            await using var cmd = connection.CreateCommand();
            cmd.CommandText =
                "SELECT id, title, director, release_year, runtime_minutes, synopsis, created_at, updated_at " +
                "FROM movies ORDER BY id";

            await using var reader = await cmd.ExecuteReaderAsync(ct);
            while (await reader.ReadAsync(ct))
            {
                movies.Add(MapMovieRow(reader));
            }

            // N+1 genre fetch — mirrors REST's pattern (CODE-01); acceptable at 10-row scale (CONT-10).
            foreach (var movie in movies)
            {
                movie.Genres = await FetchGenresAsync(connection, movie.Id, ct);
            }

            return movies;
        }
        finally
        {
            if (ownsConnection)
                await connection.DisposeAsync();
        }
    }

    public async Task<MovieDto?> GetMovieByIdAsync(long id, CancellationToken ct = default)
    {
        var connection = await OpenConnectionAsync(ct);
        var ownsConnection = _sharedConnection is null;
        try
        {
            await using var cmd = connection.CreateCommand();
            cmd.CommandText =
                "SELECT id, title, director, release_year, runtime_minutes, synopsis, created_at, updated_at " +
                "FROM movies WHERE id = @id";
            cmd.Parameters.AddWithValue("@id", id);

            await using var reader = await cmd.ExecuteReaderAsync(ct);
            if (!await reader.ReadAsync(ct))
                return null;

            var movie = MapMovieRow(reader);
            // Close reader before running genre query on the same connection.
            await reader.CloseAsync();

            movie.Genres = await FetchGenresAsync(connection, movie.Id, ct);
            return movie;
        }
        finally
        {
            if (ownsConnection)
                await connection.DisposeAsync();
        }
    }

    private static MovieDto MapMovieRow(SqliteDataReader reader)
    {
        var runtimeOrdinal = reader.GetOrdinal("runtime_minutes");
        var synopsisOrdinal = reader.GetOrdinal("synopsis");
        var directorOrdinal = reader.GetOrdinal("director");

        return new MovieDto
        {
            Id = reader.GetInt64(reader.GetOrdinal("id")),
            Title = reader.GetString(reader.GetOrdinal("title")),
            Director = reader.IsDBNull(directorOrdinal)
                ? string.Empty
                : reader.GetString(directorOrdinal),
            ReleaseYear = reader.GetInt32(reader.GetOrdinal("release_year")),
            RuntimeMinutes = reader.IsDBNull(runtimeOrdinal)
                ? null
                : reader.GetInt32(runtimeOrdinal),
            Synopsis = reader.IsDBNull(synopsisOrdinal)
                ? null
                : reader.GetString(synopsisOrdinal),
            // Timestamps read as raw strings — no DateTime rebinding (CONT-09).
            CreatedAt = reader.GetString(reader.GetOrdinal("created_at")),
            UpdatedAt = reader.GetString(reader.GetOrdinal("updated_at")),
        };
    }

    private static async Task<List<GenreDto>> FetchGenresAsync(
        SqliteConnection connection, long movieId, CancellationToken ct)
    {
        await using var cmd = connection.CreateCommand();
        cmd.CommandText =
            "SELECT g.id, g.name " +
            "FROM genres g " +
            "INNER JOIN movie_genres mg ON g.id = mg.genre_id " +
            "WHERE mg.movie_id = @movieId " +
            "ORDER BY g.id";
        cmd.Parameters.AddWithValue("@movieId", movieId);

        var genres = new List<GenreDto>();
        await using var reader = await cmd.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
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
