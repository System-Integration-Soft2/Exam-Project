using CoreWCF;
using SoapService.Contracts;
using SoapService.Contracts.Dtos;
using SoapService.Faults;
using SoapService.Repositories;
using SoapService.Validation;

namespace SoapService.Services;

public class MovieService : IMovieService
{
    private readonly IMovieRepository _repo;

    public MovieService(IMovieRepository repo)
    {
        _repo = repo;
    }

    public MovieListResult ListMovies()
    {
        var list = _repo.ListMovies();
        return new MovieListResult { Items = list.ToList() };
    }

    public MovieDto GetMovieById(GetMovieByIdRequest request)
    {
        var movie = _repo.GetMovieById(request.Id);
        if (movie is null)
        {
            throw new FaultException<NotFoundFault>(
                new NotFoundFault
                {
                    Message = $"Movie {request.Id} not found",
                    MovieId = request.Id,
                },
                new FaultReason($"Movie {request.Id} not found"));
        }
        return movie;
    }

    public MovieDto CreateMovie(CreateMovieRequest request)
    {
        // CoreWCF deserializes a missing <GenreIds> element to null, so we normalize it to empty list instead
        request.GenreIds ??= new List<int>();

        MovieValidator.Validate(request);

        if (request.GenreIds.Count > 0)
        {
            var missingIds = _repo.FindMissingGenreIds(request.GenreIds);
            if (missingIds.Count > 0)
            {
                var msg = $"Unknown genre id(s): {string.Join(", ", missingIds)}";
                throw new FaultException<ValidationFault>(
                    new ValidationFault
                    {
                        Message = msg,
                        Code = "validation_error",
                        Errors = missingIds.Select(id => $"genre_id {id} does not exist").ToList(),
                    },
                    new FaultReason(msg));
            }
        }

        var newId = _repo.CreateMovie(request);

        return _repo.GetMovieById(newId)!;
    }

    public MovieDto UpdateMovie(UpdateMovieRequest request)
    {
        // CoreWCF deserializes a missing <GenreIds> element to null, so we normalize it to empty list instead
        request.GenreIds ??= new List<int>();

        MovieValidator.Validate(request);

        if (request.GenreIds.Count > 0)
        {
            var missingIds = _repo.FindMissingGenreIds(request.GenreIds);
            if (missingIds.Count > 0)
            {
                var msg = $"Unknown genre id(s): {string.Join(", ", missingIds)}";
                throw new FaultException<ValidationFault>(
                    new ValidationFault
                    {
                        Message = msg,
                        Code = "validation_error",
                        Errors = missingIds.Select(id => $"genre_id {id} does not exist").ToList(),
                    },
                    new FaultReason(msg));
            }
        }

        if (!_repo.UpdateMovie(request))
        {
            throw new FaultException<NotFoundFault>(
                new NotFoundFault
                {
                    Message = $"Movie {request.Id} not found",
                    MovieId = request.Id,
                },
                new FaultReason($"Movie {request.Id} not found"));
        }

        return _repo.GetMovieById(request.Id)!;
    }

    public void DeleteMovie(DeleteMovieRequest request)
    {
        if (!_repo.DeleteMovie(request.Id))
        {
            throw new FaultException<NotFoundFault>(
                new NotFoundFault
                {
                    Message = $"Movie {request.Id} not found",
                    MovieId = request.Id,
                },
                new FaultReason($"Movie {request.Id} not found"));
        }
    }
}
