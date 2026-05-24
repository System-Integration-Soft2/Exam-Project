using CoreWCF;
using FluentAssertions;
using SoapService.Contracts.Dtos;
using SoapService.Faults;
using SoapService.Validation;
using Xunit;

namespace SoapService.Tests.Validation;

/// <summary>
/// Pure unit tests for MovieValidator — no DB required.
/// Each test exercises one validation rule with an invalid input and asserts
/// FaultException&lt;ValidationFault&gt; is thrown.
/// </summary>
public class MovieValidatorTests
{
    // ── Title ──────────────────────────────────────────────────────────────

    [Fact]
    public void Title_Empty_Throws()
    {
        var req = ValidCreate();
        req.Title = string.Empty;

        var act = () => MovieValidator.Validate(req);

        act.Should().Throw<FaultException<ValidationFault>>()
            .Which.Detail.Code.Should().Be("validation_error");
    }

    [Fact]
    public void Title_TooLong_Throws()
    {
        var req = ValidCreate();
        req.Title = new string('x', 256); // 256 chars — limit is 255

        var act = () => MovieValidator.Validate(req);

        act.Should().Throw<FaultException<ValidationFault>>();
    }

    // ── ReleaseYear ────────────────────────────────────────────────────────

    [Fact]
    public void ReleaseYear_TooEarly_Throws()
    {
        var req = ValidCreate();
        req.ReleaseYear = 1887; // min is 1888

        var act = () => MovieValidator.Validate(req);

        act.Should().Throw<FaultException<ValidationFault>>();
    }

    [Fact]
    public void ReleaseYear_TooLate_Throws()
    {
        var req = ValidCreate();
        req.ReleaseYear = 2101; // max is 2100

        var act = () => MovieValidator.Validate(req);

        act.Should().Throw<FaultException<ValidationFault>>();
    }

    // ── RuntimeMinutes ─────────────────────────────────────────────────────

    [Fact]
    public void RuntimeMinutes_Zero_Throws()
    {
        var req = ValidCreate();
        req.RuntimeMinutes = 0;

        var act = () => MovieValidator.Validate(req);

        act.Should().Throw<FaultException<ValidationFault>>();
    }

    [Fact]
    public void RuntimeMinutes_Negative_Throws()
    {
        var req = ValidCreate();
        req.RuntimeMinutes = -1;

        var act = () => MovieValidator.Validate(req);

        act.Should().Throw<FaultException<ValidationFault>>();
    }

    // ── Synopsis ───────────────────────────────────────────────────────────

    [Fact]
    public void Synopsis_TooLong_Throws()
    {
        var req = ValidCreate();
        req.Synopsis = new string('s', 5001); // limit is 5000

        var act = () => MovieValidator.Validate(req);

        act.Should().Throw<FaultException<ValidationFault>>();
    }

    // ── Director ───────────────────────────────────────────────────────────

    [Fact]
    public void Director_TooLong_Throws()
    {
        var req = ValidCreate();
        req.Director = new string('d', 256); // limit is 255

        var act = () => MovieValidator.Validate(req);

        act.Should().Throw<FaultException<ValidationFault>>();
    }

    // ── GenreIds ───────────────────────────────────────────────────────────

    [Fact]
    public void GenreIds_TooMany_Throws()
    {
        var req = ValidCreate();
        req.GenreIds = Enumerable.Range(1, 21).ToList(); // limit is 20

        var act = () => MovieValidator.Validate(req);

        act.Should().Throw<FaultException<ValidationFault>>();
    }

    [Fact]
    public void GenreIds_Duplicates_Throws()
    {
        var req = ValidCreate();
        req.GenreIds = new List<int> { 1, 1, 2 }; // duplicate id=1

        var act = () => MovieValidator.Validate(req);

        act.Should().Throw<FaultException<ValidationFault>>()
            .Which.Detail.Code.Should().Be("validation_error");
    }

    // ── Happy path (no throw) ──────────────────────────────────────────────

    [Fact]
    public void ValidRequest_DoesNotThrow()
    {
        var req = ValidCreate();

        var act = () => MovieValidator.Validate(req);

        act.Should().NotThrow();
    }

    [Fact]
    public void NullableFields_AllNull_DoesNotThrow()
    {
        var req = new CreateMovieRequest
        {
            Title = "Test Movie",
            Director = null,
            ReleaseYear = 2000,
            RuntimeMinutes = null,
            Synopsis = null,
            GenreIds = new List<int>(),
        };

        var act = () => MovieValidator.Validate(req);

        act.Should().NotThrow();
    }

    // ── Helpers ────────────────────────────────────────────────────────────

    private static CreateMovieRequest ValidCreate() => new()
    {
        Title = "Test Movie",
        Director = "Test Director",
        ReleaseYear = 2000,
        RuntimeMinutes = 120,
        Synopsis = "A test synopsis.",
        GenreIds = new List<int> { 1, 2 },
    };
}
