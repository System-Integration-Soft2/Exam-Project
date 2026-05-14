using Microsoft.Data.Sqlite;

namespace SoapService.Endpoints;

public static class HealthEndpoint
{
    public static void MapHealthEndpoint(this WebApplication app)
    {
        app.MapGet("/healthz", async (IConfiguration config) =>
        {
            // DATABASE_PATH is validated at startup (Program.cs); the ! is honest about that precondition.
            var dbPath = config["DATABASE_PATH"]!;
            var connectionString = $"Data Source={dbPath}";

            try
            {
                await using var connection = new SqliteConnection(connectionString);
                await connection.OpenAsync();
                await using var command = connection.CreateCommand();
                command.CommandText = "SELECT 1";
                await command.ExecuteScalarAsync();

                return Results.Ok(new { db = "ok" });
            }
            catch (SqliteException ex)
            {
                app.Logger.LogError(ex, "Health check: SQLite SELECT 1 failed against {DbPath}", dbPath);
                return Results.Json(new { db = "error" }, statusCode: StatusCodes.Status503ServiceUnavailable);
            }
            // Broad catch: any unexpected I/O failure (IOException, UnauthorizedAccessException, etc.)
            // also returns 503. The health endpoint contract is binary (ok / error); we never want
            // to leak an unhandled 500 with stack trace to the orchestrator.
            catch (Exception ex)
            {
                app.Logger.LogError(ex, "Health check: unexpected failure against {DbPath}", dbPath);
                return Results.Json(new { db = "error" }, statusCode: StatusCodes.Status503ServiceUnavailable);
            }
        });
    }
}
