using System.Runtime.Serialization;

namespace SoapService.Contracts.Dtos;

[DataContract(Namespace = "http://soapservice.example.com/movies")]
public class GenreDto
{
    [DataMember(Order = 1)]
    public long Id { get; set; }

    [DataMember(Order = 2)]
    public string Name { get; set; } = string.Empty;
}
