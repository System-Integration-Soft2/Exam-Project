using CoreWCF;
using FluentAssertions;
using Microsoft.Data.Sqlite;
using SoapService.Contracts.Dtos;
using SoapService.Faults;
using SoapService.Repositories;
using SoapService.Tests.Fixtures;
using Xunit;

namespace SoapService.Tests.Repositories;

/// <summary>
/// Integration tests for MovieRepository write methods against an in-memory SQLite DB.
/// Each test class gets its own fixture instance so writes don't bleed across test classes.
/// </summary>
public class MovieRepositoryWriteTests : IClassFixture<InMemoryDbFixture>
{
    private readonly MovieRepository _repo;
    private readonly SqliteConnection _connection;

    public MovieRepositoryWriteTests(InMemoryDbFixture fixture)
    {
        _connection = fixture.Connection;
        _repo = new MovieRepository(_connection);
    }

    // ── CreateMovie ────────────────────────────────────────────────────────

    [Fact]
    public void CreateMovie_PersistsRow()
    {
        var req = new CreateMovieRequest
        {
            Title = "New Movie",
            Director = "Some Director",
            ReleaseYear = 2020,
            RuntimeMinutes = 90,
            Synopsis = "A synopsis.",
            GenreIds = new List<int> { 1 }, // Action (seeded)
        };

        var newId = _repo.CreateMovie(req);

        newId.Should().BeGreaterThan(0, "CreateMovie must return the new row id");

        var fetched = _repo.GetMovieById(newId);
        fetched.Should().NotBeNull();
        fetched!.Title.Should().Be("New Movie");
        fetched.Director.Should().Be("Some Director");
        fetched.ReleaseYear.Should().Be(2020);
        fetched.RuntimeMinutes.Should().Be(90);
        fetched.Synopsis.Should().Be("A synopsis.");
    }

    [Fact]
    public void CreateMovie_PersistsGenreLinks()
    {
        var req = new CreateMovieRequest
        {
            Title = "Genre Link Movie",
            Director = null,
            ReleaseYear = 2021,
            RuntimeMinutes = null,
            Synopsis = null,
            GenreIds = new List<int> { 1, 2 }, // Action + Drama (seeded)
        };

        var newId = _repo.CreateMovie(req);

        var fetched = _repo.GetMovieById(newId);
        fetched.Should().NotBeNull();
        fetched!.Genres.Should().HaveCount(2);
        fetched.Genres.Select(g => g.Id).Should().BeEquivalentTo(new[] { 1L, 2L });
    }

    [Fact]
    public void CreateMovie_UnknownGenreId_Throws()
    {
        var req = new CreateMovieRequest
        {
            Title = "Bad Genre Movie",
            Director = null,
            ReleaseYear = 2022,
            RuntimeMinutes = null,
            Synopsis = null,
            GenreIds = new List<int> { 999 }, // does not exist
        };

        var act = () => _repo.CreateMovie(req);

        act.Should().Throw<FaultException<ValidationFault>>()
            .Which.Detail.Code.Should().Be("validation_error");
    }

    // ── UpdateMovie ────────────────────────────────────────────────────────

    [Fact]
    public void UpdateMovie_BumpsUpdatedAt()
    {
        // Insert a movie first
        var createReq = new CreateMovieRequest
        {
            Title = "Update Timestamp Test",
            Director = "Director A",
            ReleaseYear = 2010,
            RuntimeMinutes = 100,
            Synopsis = null,
            GenreIds = new List<int> { 1 },
        };
        var newId = _repo.CreateMovie(createReq);

        var original = _repo.GetMovieById(newId)!;
        var createdAt = original.CreatedAt;

        // SQLite strftime resolution is 1 second; sleep briefly to ensure a different timestamp.
        // We use a direct SQL update to set created_at to a past value so the comparison is reliable.
        using var cmd = _connection.CreateCommand();
        cmd.CommandText = "UPDATE movies SET created_at = '2000-01-01T00:00:00', updated_at = '2000-01-01T00:00:00' WHERE id = @id";
        cmd.Parameters.AddWithValue("@id", newId);
        cmd.ExecuteNonQuery();

        var updateReq = new UpdateMovieRequest
        {
            Id = newId,
            Title = "Update Timestamp Test (edited)",
            Director = "Director B",
            ReleaseYear = 2011,
            RuntimeMinutes = 110,
            Synopsis = "Updated synopsis.",
            GenreIds = new List<int> { 2 },
        };

        _repo.UpdateMovie(updateReq);

        var updated = _repo.GetMovieById(newId)!;

        // updated_at must differ from the forced-past value
        updated.UpdatedAt.Should().NotBe("2000-01-01T00:00:00",
            "UpdateMovie must set updated_at via strftime (CONT-05)");

        // Both timestamps must match YYYY-MM-DDTHH:MM:SS format (CONT-09)
        updated.CreatedAt.Should().MatchRegex(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",
            "created_at must be ISO 8601 without timezone suffix");
        updated.UpdatedAt.Should().MatchRegex(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",
            "updated_at must be ISO 8601 without timezone suffix");

        // updated_at must be strictly later than the forced-past created_at
        updated.UpdatedAt.Should().NotBe(updated.CreatedAt,
            "updated_at must differ from created_at after an update");
    }

    [Fact]
    public void UpdateMovie_FullReplaceGenres()
    {
        // Insert with Action + Sci-Fi
        var createReq = new CreateMovieRequest
        {
            Title = "Genre Replace Test",
            Director = null,
            ReleaseYear = 2015,
            RuntimeMinutes = null,
            Synopsis = null,
            GenreIds = new List<int> { 1, 3 }, // Action + Sci-Fi
        };
        var newId = _repo.CreateMovie(createReq);

        // Update with only Drama
        var updateReq = new UpdateMovieRequest
        {
            Id = newId,
            Title = "Genre Replace Test",
            Director = null,
            ReleaseYear = 2015,
            RuntimeMinutes = null,
            Synopsis = null,
            GenreIds = new List<int> { 2 }, // Drama only
        };
        _repo.UpdateMovie(updateReq);

        var updated = _repo.GetMovieById(newId)!;
        updated.Genres.Should().HaveCount(1, "full-replace semantics: only Drama should remain");
        updated.Genres.Single().Id.Should().Be(2L, "Drama has id=2 in seed data");
    }

    [Fact]
    public void UpdateMovie_MissingId_Throws()
    {
        var req = new UpdateMovieRequest
        {
            Id = 999_999,
            Title = "Ghost Movie",
            Director = null,
            ReleaseYear = 2000,
            RuntimeMinutes = null,
            Synopsis = null,
            GenreIds = new List<int>(),
        };

        var act = () => _repo.UpdateMovie(req);

        act.Should().Throw<FaultException<NotFoundFault>>()
            .Which.Detail.MovieId.Should().Be(999_999);
    }
}
