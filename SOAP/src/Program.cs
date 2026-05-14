using CoreWCF;
using CoreWCF.Configuration;
using CoreWCF.Description;
using SoapService.Contracts;
using SoapService.Endpoints;
using SoapService.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddServiceModelServices();
builder.Services.AddServiceModelMetadata();
builder.Services.AddSingleton<IServiceBehavior, UseRequestHeadersForMetadataAddressBehavior>();

builder.Services.AddTransient<MovieService>();

var app = builder.Build();

app.UseServiceModel(serviceBuilder =>
{
    serviceBuilder.AddService<MovieService>(serviceOptions =>
    {
        serviceOptions.DebugBehavior.IncludeExceptionDetailInFaults = false;
    });

    serviceBuilder.AddServiceEndpoint<MovieService, IMovieService>(
        new BasicHttpBinding(),
        "/movies.svc");
});

var serviceMetadataBehavior = app.Services.GetRequiredService<ServiceMetadataBehavior>();
serviceMetadataBehavior.HttpGetEnabled = true;

// Fail loud at startup if DATABASE_PATH is missing — mirrors REST's JWT_SECRET guard (vision §7).
// HealthEndpoint and future repository code depend on this being set; a silent default would mask
// misconfiguration until the first request.
if (string.IsNullOrWhiteSpace(app.Configuration["DATABASE_PATH"]))
    throw new InvalidOperationException("DATABASE_PATH environment variable is required");

app.MapHealthEndpoint();

app.Run();
