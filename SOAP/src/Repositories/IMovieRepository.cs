using SoapService.Contracts.Dtos;

namespace SoapService.Repositories;

public interface IMovieRepository
{
    IReadOnlyList<MovieDto> ListMovies();
    MovieDto? GetMovieById(long id);

    List<int> FindMissingGenreIds(List<int> genreIds);
    long CreateMovie(CreateMovieRequest request);
    bool UpdateMovie(UpdateMovieRequest request);
    bool DeleteMovie(long id);
}
