using Microsoft.Data.Sqlite;

namespace SoapService.Tests.Fixtures;

/// <summary>
/// xUnit class fixture that provides a shared in-memory SQLite connection
/// seeded with the repo-root seed.sql schema and data.
///
/// :memory: gotcha: each SqliteConnection("Data Source=:memory:") gets its own
/// private database. We keep ONE connection open for the fixture lifetime so all
/// tests in the same class share the same in-memory database.
/// </summary>
public sealed class InMemoryDbFixture : IDisposable
{
    public SqliteConnection Connection { get; }

    public InMemoryDbFixture()
    {
        Connection = new SqliteConnection("Data Source=:memory:");
        Connection.Open();
        ApplySeed();
    }

    private void ApplySeed()
    {
        // seed.sql is at the repo root — two levels up from SOAP/tests/.
        // This path is intentional: seed.sql must NOT be copied into src/.
        var seedPath = Path.Combine(
            AppContext.BaseDirectory,
            "..", "..", "..", "..", "..", "seed.sql");

        var sql = File.ReadAllText(seedPath);

        using var command = Connection.CreateCommand();
        command.CommandText = sql;
        command.ExecuteNonQuery();
    }

    public void Dispose()
    {
        Connection.Dispose();
    }
}
