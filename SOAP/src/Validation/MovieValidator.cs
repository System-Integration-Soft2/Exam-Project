using CoreWCF;
using SoapService.Contracts.Dtos;
using SoapService.Faults;

namespace SoapService.Validation;

public static class MovieValidator
{
    private const int TitleMaxLength = 255;
    private const int DirectorMaxLength = 255;
    private const int SynopsisMaxLength = 5000;
    private const int ReleaseYearMin = 1888;
    private const int ReleaseYearMax = 2100;
    private const int GenreIdsMaxCount = 20;

    public static void Validate(CreateMovieRequest request)
    {
        ValidateTitle(request.Title);
        ValidateDirector(request.Director);
        ValidateReleaseYear(request.ReleaseYear);
        ValidateRuntimeMinutes(request.RuntimeMinutes);
        ValidateSynopsis(request.Synopsis);
        ValidateGenreIdCount(request.GenreIds);
    }


    public static void Validate(UpdateMovieRequest request)
    {
        ValidateTitle(request.Title);
        ValidateDirector(request.Director);
        ValidateReleaseYear(request.ReleaseYear);
        ValidateRuntimeMinutes(request.RuntimeMinutes);
        ValidateSynopsis(request.Synopsis);
        ValidateGenreIdCount(request.GenreIds);
    }

    private static void ValidateTitle(string title)
    {
        if (string.IsNullOrEmpty(title))
            Throw("title is required");
        if (title.Length > TitleMaxLength)
            Throw($"title must be at most {TitleMaxLength} characters");
    }

    private static void ValidateDirector(string? director)
    {
        if (director is not null && director.Length > DirectorMaxLength)
            Throw($"director must be at most {DirectorMaxLength} characters");
    }

    private static void ValidateReleaseYear(int year)
    {
        if (year < ReleaseYearMin || year > ReleaseYearMax)
            Throw($"release_year must be between {ReleaseYearMin} and {ReleaseYearMax}");
    }

    private static void ValidateRuntimeMinutes(int? runtimeMinutes)
    {
        if (runtimeMinutes.HasValue && runtimeMinutes.Value <= 0)
            Throw("runtime_minutes must be greater than 0 when provided");
    }

    private static void ValidateSynopsis(string? synopsis)
    {
        if (synopsis is not null && synopsis.Length > SynopsisMaxLength)
            Throw($"synopsis must be at most {SynopsisMaxLength} characters");
    }

    private static void ValidateGenreIdCount(List<int> genreIds)
    {
        if (genreIds.Count > GenreIdsMaxCount)
            Throw($"genre_ids must contain at most {GenreIdsMaxCount} entries");
        if (genreIds.Distinct().Count() != genreIds.Count)
            Throw("Duplicate genre IDs are not allowed");
    }

    private static void Throw(string message)
    {
        var fault = new ValidationFault
        {
            Message = message,
            Code = "validation_error",
            Errors = new List<string> { message },
        };
        throw new FaultException<ValidationFault>(fault, new FaultReason(message));
    }
}
