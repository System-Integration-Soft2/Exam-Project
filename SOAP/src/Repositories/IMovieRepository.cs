using SoapService.Contracts.Dtos;

namespace SoapService.Repositories;

public interface IMovieRepository
{
    IReadOnlyList<MovieDto> ListMovies();
    MovieDto? GetMovieById(long id);
}
