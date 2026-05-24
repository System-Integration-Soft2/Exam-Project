using Microsoft.Data.Sqlite;

namespace SoapService.Endpoints;


public static class HealthChecker
{
    public static async Task<bool> CheckDbAsync(string connectionString)
    {
        try
        {
            await using var connection = new SqliteConnection(connectionString);
            await connection.OpenAsync();
            await using var command = connection.CreateCommand();
            command.CommandText = "SELECT 1";
            await command.ExecuteScalarAsync();
            return true;
        }
        catch (Exception)
        {
            // Any failure (SqliteException, IOException, UnauthorizedAccessException, etc.)
            // is treated as unhealthy. The caller logs and returns 503.
            return false;
        }
    }
}

public static class HealthEndpoint
{
    public static void MapHealthEndpoint(this WebApplication app)
    {
        app.MapGet("/healthz", async (IConfiguration config) =>
        {
            var dbPath = config["DATABASE_PATH"]!;
            var connectionString = $"Data Source={dbPath}";

            var isHealthy = await HealthChecker.CheckDbAsync(connectionString);

            if (isHealthy)
                return Results.Ok(new { db = "ok" });

            app.Logger.LogError("Health check: SQLite SELECT 1 failed against {DbPath}", dbPath);
            return Results.Json(new { db = "error" }, statusCode: StatusCodes.Status503ServiceUnavailable);
        });
    }
}
