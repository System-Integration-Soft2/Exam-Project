using System.Runtime.Serialization;

namespace SoapService.Contracts.Dtos;

[DataContract(Namespace = "http://soapservice.example.com/movies")]
public class GetMovieByIdRequest
{
    [DataMember(Order = 1)]
    public long Id { get; set; }
}
