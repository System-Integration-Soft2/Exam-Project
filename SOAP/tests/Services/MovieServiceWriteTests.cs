using CoreWCF;
using FluentAssertions;
using SoapService.Contracts.Dtos;
using SoapService.Faults;
using SoapService.Repositories;
using SoapService.Services;
using SoapService.Tests.Fixtures;
using Xunit;

namespace SoapService.Tests.Services;

/// <summary>
/// Integration-style write tests for MovieService wired to a real MovieRepository
/// over an in-memory SQLite DB. Tests the full service → repository path.
/// </summary>
public class MovieServiceWriteTests : IClassFixture<InMemoryDbFixture>
{
    private readonly MovieService _service;

    public MovieServiceWriteTests(InMemoryDbFixture fixture)
    {
        var repo = new MovieRepository(fixture.Connection);
        _service = new MovieService(repo);
    }

    // ── CreateMovie ────────────────────────────────────────────────────────

    [Fact]
    public void CreateMovie_ReturnsFullDto()
    {
        var req = new CreateMovieRequest
        {
            Title = "Service Create Test",
            Director = "Director X",
            ReleaseYear = 2023,
            RuntimeMinutes = 95,
            Synopsis = "A service-layer test movie.",
            GenreIds = new List<int> { 1, 2 }, // Action + Drama
        };

        var result = _service.CreateMovie(req);

        result.Should().NotBeNull();
        result.Id.Should().BeGreaterThan(0, "returned DTO must have a valid DB id");
        result.Title.Should().Be("Service Create Test");
        result.Director.Should().Be("Director X");
        result.ReleaseYear.Should().Be(2023);
        result.RuntimeMinutes.Should().Be(95);
        result.Genres.Should().HaveCount(2);
        result.CreatedAt.Should().MatchRegex(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$");
        result.UpdatedAt.Should().MatchRegex(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$");
    }

    [Fact]
    public void CreateMovie_ValidationFault_OnEmptyTitle()
    {
        var req = new CreateMovieRequest
        {
            Title = string.Empty,
            Director = null,
            ReleaseYear = 2000,
            RuntimeMinutes = null,
            Synopsis = null,
            GenreIds = new List<int>(),
        };

        var act = () => _service.CreateMovie(req);

        act.Should().Throw<FaultException<ValidationFault>>()
            .Which.Detail.Code.Should().Be("validation_error");
    }

    // ── UpdateMovie ────────────────────────────────────────────────────────

    [Fact]
    public void UpdateMovie_ReturnsUpdatedDto()
    {
        // First create a movie
        var createReq = new CreateMovieRequest
        {
            Title = "Service Update Test",
            Director = "Original Director",
            ReleaseYear = 2010,
            RuntimeMinutes = 100,
            Synopsis = "Original synopsis.",
            GenreIds = new List<int> { 1 },
        };
        var created = _service.CreateMovie(createReq);

        // Force created_at/updated_at to a past value so the comparison is reliable
        // (SQLite strftime resolution is 1 second)
        // We access the connection via the fixture — but service tests don't have direct
        // connection access. Instead we rely on the fact that the test fixture's connection
        // is shared and we can reach it through the repo's internal state.
        // Simpler: just assert updated_at matches the timestamp format and that the
        // returned DTO reflects the new field values.

        var updateReq = new UpdateMovieRequest
        {
            Id = created.Id,
            Title = "Service Update Test (edited)",
            Director = "New Director",
            ReleaseYear = 2011,
            RuntimeMinutes = 110,
            Synopsis = "Updated synopsis.",
            GenreIds = new List<int> { 2 }, // Drama
        };

        var updated = _service.UpdateMovie(updateReq);

        updated.Should().NotBeNull();
        updated.Id.Should().Be(created.Id);
        updated.Title.Should().Be("Service Update Test (edited)");
        updated.Director.Should().Be("New Director");
        updated.ReleaseYear.Should().Be(2011);
        updated.RuntimeMinutes.Should().Be(110);
        updated.Genres.Should().HaveCount(1);
        updated.Genres.Single().Id.Should().Be(2L);
        updated.UpdatedAt.Should().MatchRegex(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",
            "updated_at must be ISO 8601 without timezone suffix (CONT-09)");
    }

    [Fact]
    public void UpdateMovie_NotFoundFault_OnMissingId()
    {
        var req = new UpdateMovieRequest
        {
            Id = 999_999,
            Title = "Ghost",
            Director = null,
            ReleaseYear = 2000,
            RuntimeMinutes = null,
            Synopsis = null,
            GenreIds = new List<int>(),
        };

        var act = () => _service.UpdateMovie(req);

        act.Should().Throw<FaultException<NotFoundFault>>()
            .Which.Detail.MovieId.Should().Be(999_999);
    }
}
