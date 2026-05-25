using System.Runtime.Serialization;

namespace SoapService.Faults;

[DataContract(Namespace = "http://soapservice.example.com/movies")]
public class NotFoundFault
{
    [DataMember(Order = 1)]
    public string Message { get; set; } = string.Empty;

    [DataMember(Order = 2)]
    public long MovieId { get; set; }
}
