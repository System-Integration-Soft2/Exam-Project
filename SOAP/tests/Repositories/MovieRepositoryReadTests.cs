using FluentAssertions;
using SoapService.Repositories;
using SoapService.Tests.Fixtures;
using Xunit;

namespace SoapService.Tests.Repositories;

/// <summary>
/// Integration-style read tests for MovieRepository against an in-memory SQLite DB
/// seeded with seed.sql data. Uses InMemoryDbFixture to share one open connection
/// across all tests in this class (avoids :memory: isolation gotcha).
/// </summary>
public class MovieRepositoryReadTests : IClassFixture<InMemoryDbFixture>
{
    private readonly MovieRepository _repo;

    public MovieRepositoryReadTests(InMemoryDbFixture fixture)
    {
        _repo = new MovieRepository(fixture.Connection);
    }

    [Fact]
    public async Task ListMoviesAsync_ReturnsAllSeededMovies()
    {
        var movies = await _repo.ListMoviesAsync();

        movies.Should().HaveCount(10, "seed.sql inserts exactly 10 movies");
    }

    [Fact]
    public async Task ListMoviesAsync_EachMovieHasItsGenres()
    {
        var movies = await _repo.ListMoviesAsync();

        // Inception (id=1) has Action + Sci-Fi per seed.sql
        var inception = movies.Single(m => m.Id == 1);
        inception.Genres.Should().HaveCount(2);
        inception.Genres.Select(g => g.Name).Should().Contain(new[] { "Action", "Sci-Fi" });
    }

    [Fact]
    public async Task GetMovieByIdAsync_ReturnsNullForMissingId()
    {
        var result = await _repo.GetMovieByIdAsync(999);

        result.Should().BeNull("id 999 does not exist in the seeded data");
    }

    [Fact]
    public async Task GetMovieByIdAsync_ReturnsMovieWhenIdExists()
    {
        var result = await _repo.GetMovieByIdAsync(1);

        result.Should().NotBeNull();
        result!.Id.Should().Be(1);
        result.Title.Should().Be("Inception");
    }

    [Fact]
    public async Task GetMovieByIdAsync_ReturnsTimestampsAsRawStrings()
    {
        var result = await _repo.GetMovieByIdAsync(1);

        result.Should().NotBeNull();
        // Timestamps must be raw strings in YYYY-MM-DDTHH:MM:SS format (CONT-09).
        // They must NOT have a timezone suffix (no 'Z', no '+00:00').
        result!.CreatedAt.Should().MatchRegex(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",
            "timestamps must be ISO 8601 without timezone suffix per CONT-09");
        result.UpdatedAt.Should().MatchRegex(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",
            "timestamps must be ISO 8601 without timezone suffix per CONT-09");
    }
}
