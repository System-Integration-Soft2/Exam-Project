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
/// Integration-style read tests for MovieService wired to a real MovieRepository
/// over an in-memory SQLite DB. No mocking — tests the full service → repository path.
/// </summary>
public class MovieServiceReadTests : IClassFixture<InMemoryDbFixture>
{
    private readonly MovieService _service;

    public MovieServiceReadTests(InMemoryDbFixture fixture)
    {
        var repo = new MovieRepository(fixture.Connection);
        _service = new MovieService(repo);
    }

    [Fact]
    public void ListMovies_ReturnsMovieListResult_WithAllSeededMovies()
    {
        var result = _service.ListMovies();

        result.Should().NotBeNull();
        result.Items.Should().HaveCount(10, "seed.sql inserts exactly 10 movies");
    }

    [Fact]
    public void GetMovieById_ReturnsMovie_WhenIdExists()
    {
        var result = _service.GetMovieById(new GetMovieByIdRequest { Id = 1 });

        result.Should().NotBeNull();
        result.Id.Should().Be(1);
        result.Title.Should().Be("Inception");
    }

    [Fact]
    public void GetMovieById_ThrowsFaultException_WhenMovieMissing()
    {
        var act = () => _service.GetMovieById(new GetMovieByIdRequest { Id = 999 });

        act.Should().Throw<FaultException<NotFoundFault>>()
            .Which.Detail.MovieId.Should().Be(999);
    }
}
