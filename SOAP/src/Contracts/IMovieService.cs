using CoreWCF;
using SoapService.Contracts.Dtos;

namespace SoapService.Contracts;

[ServiceContract(Namespace = "http://soapservice.example.com/movies/service")]
public interface IMovieService
{
    [OperationContract]
    MovieListResult ListMovies();

    [OperationContract]
    MovieDto GetMovieById(GetMovieByIdRequest request);

    [OperationContract]
    MovieDto CreateMovie(CreateMovieRequest request);

    [OperationContract]
    MovieDto UpdateMovie(UpdateMovieRequest request);
}
