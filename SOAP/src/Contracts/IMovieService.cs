using CoreWCF;
using SoapService.Contracts.Dtos;
using SoapService.Faults;

namespace SoapService.Contracts;

[ServiceContract(Namespace = "http://soapservice.example.com/movies/service")]
public interface IMovieService
{
    [OperationContract]
    MovieListResult ListMovies();

    [OperationContract]
    [FaultContract(typeof(NotFoundFault))]
    MovieDto GetMovieById(GetMovieByIdRequest request);

    [OperationContract]
    MovieDto CreateMovie(CreateMovieRequest request);

    [OperationContract]
    MovieDto UpdateMovie(UpdateMovieRequest request);
}
