using SoapService.Contracts.Dtos;

namespace SoapService.Repositories;

public interface IMovieRepository
{
    Task<IReadOnlyList<MovieDto>> ListMoviesAsync(CancellationToken ct = default);
    Task<MovieDto?> GetMovieByIdAsync(long id, CancellationToken ct = default);
}
