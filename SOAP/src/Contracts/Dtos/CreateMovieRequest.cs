using System.Runtime.Serialization;

namespace SoapService.Contracts.Dtos;

[DataContract(Namespace = "http://soapservice.example.com/movies")]
public class CreateMovieRequest
{
    [DataMember(Order = 1)]
    public string Title { get; set; } = string.Empty;

    [DataMember(Order = 2)]
    public string Director { get; set; } = string.Empty;

    [DataMember(Order = 3)]
    public int ReleaseYear { get; set; }

    [DataMember(Order = 4)]
    public int? RuntimeMinutes { get; set; }

    [DataMember(Order = 5)]
    public string? Synopsis { get; set; }

    [DataMember(Order = 6)]
    public List<int> GenreIds { get; set; } = new();
}
