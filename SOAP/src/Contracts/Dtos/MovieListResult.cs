using System.Runtime.Serialization;

namespace SoapService.Contracts.Dtos;

// Named MovieListResult (not ListMoviesResponse) to avoid CoreWCF WSDL schema collision:
// CoreWCF generates a wrapper element named "ListMoviesResponse" for the ListMovies operation;
// if the return type is also named "ListMoviesResponse", the XSD schema declares the element twice.
[DataContract(Namespace = "http://soapservice.example.com/movies")]
public class MovieListResult
{
    [DataMember(Order = 1)]
    public List<MovieDto> Items { get; set; } = new();
}
