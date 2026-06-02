using System.Runtime.Serialization;

namespace SoapService.Faults;

// Typed SOAP fault detail for validation errors.

[DataContract(Namespace = "http://soapservice.example.com/movies")]
public class ValidationFault
{
    [DataMember(Order = 1)]
    public string Message { get; set; } = string.Empty;

    [DataMember(Order = 2)]
    public string Code { get; set; } = "validation_error";

    [DataMember(Order = 3)]
    public List<string> Errors { get; set; } = new();
}
