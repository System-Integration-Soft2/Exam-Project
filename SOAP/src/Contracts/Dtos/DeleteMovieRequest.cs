using System.Runtime.Serialization;

namespace SoapService.Contracts.Dtos;

[DataContract(Namespace = "http://soapservice.example.com/movies")]
public class DeleteMovieRequest
{
    [DataMember(Order = 1)]
    public long Id { get; set; }
}
