using SoapService.Contracts.Dtos;

namespace SoapService.Repositories;

public interface IMovieRepository
{
    IReadOnlyList<MovieDto> ListMovies();
    MovieDto? GetMovieById(long id);

    long CreateMovie(CreateMovieRequest request);
    void UpdateMovie(UpdateMovieRequest request);
}
