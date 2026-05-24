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
        // Field-level validation
        MovieValidator.Validate(request);

        var newId = _repo.CreateMovie(request);

        return _repo.GetMovieById(newId)!;
    }

    public MovieDto UpdateMovie(UpdateMovieRequest request)
    {
        // Field-level validation
        MovieValidator.Validate(request);

        _repo.UpdateMovie(request);

        return _repo.GetMovieById(request.Id)!;
    }
}
