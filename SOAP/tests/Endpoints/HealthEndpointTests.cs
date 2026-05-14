using FluentAssertions;
using SoapService.Endpoints;
using Xunit;

namespace SoapService.Tests.Endpoints;

/// <summary>
/// Tests the healthz DB-check logic in isolation.
/// Uses HealthChecker.CheckDbAsync — the extracted testable core of HealthEndpoint.
/// </summary>
public class HealthEndpointTests
{
    [Fact]
    public async Task HealthzReturns503OnDbFailure()
    {
        // Arrange: a connection string pointing at a non-existent path forces a failure.
        // SQLite will fail to open a file at /nonexistent/path/catalog.db.
        const string brokenConnectionString = "Data Source=/nonexistent/path/catalog.db";

        // Act
        var isHealthy = await HealthChecker.CheckDbAsync(brokenConnectionString);

        // Assert
        isHealthy.Should().BeFalse("a broken connection string must cause the health check to report unhealthy");
    }

    [Fact]
    public async Task HealthzReturnsOkOnValidConnection()
    {
        // Arrange: in-memory SQLite always opens successfully.
        const string goodConnectionString = "Data Source=:memory:";

        // Act
        var isHealthy = await HealthChecker.CheckDbAsync(goodConnectionString);

        // Assert
        isHealthy.Should().BeTrue("an in-memory SQLite connection must be healthy");
    }
}
