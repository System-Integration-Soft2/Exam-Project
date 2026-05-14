using CoreWCF;
using SoapService.Contracts;
using SoapService.Contracts.Dtos;
using SoapService.Faults;
using SoapService.Repositories;

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
        var list = _repo.ListMoviesAsync().GetAwaiter().GetResult();
        return new MovieListResult { Items = list.ToList() };
    }

    public MovieDto GetMovieById(GetMovieByIdRequest request)
    {
        var movie = _repo.GetMovieByIdAsync(request.Id).GetAwaiter().GetResult();
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
        throw new NotImplementedException("P3");
    }

    public MovieDto UpdateMovie(UpdateMovieRequest request)
    {
        throw new NotImplementedException("P3");
    }
}
