using FluentAssertions;
using Microsoft.AspNetCore.Http;
using SoapService.Middleware;
using Xunit;

namespace SoapService.Tests.Middleware;

/// <summary>
/// Unit tests for SecurityHeadersMiddleware.
/// Uses DefaultHttpContext — no live Kestrel needed.
/// Each case asserts X-Content-Type-Options: nosniff is present regardless of path.
/// </summary>
public class SecurityHeadersMiddlewareTests
{
    [Theory]
    [InlineData("/healthz")]
    [InlineData("/movies.svc")]
    [InlineData("/movies.svc?wsdl")]
    public async Task InvokeAsync_AddsNosniffHeader(string requestPath)
    {
        var middleware = new SecurityHeadersMiddleware(_ => Task.CompletedTask);
        var context = new DefaultHttpContext();

        // Parse path and optional query string from the test parameter.
        var queryIndex = requestPath.IndexOf('?');
        if (queryIndex >= 0)
        {
            context.Request.Path = requestPath[..queryIndex];
            context.Request.QueryString = new QueryString(requestPath[queryIndex..]);
        }
        else
        {
            context.Request.Path = requestPath;
        }

        await middleware.InvokeAsync(context);

        context.Response.Headers["X-Content-Type-Options"]
            .ToString().Should().Be("nosniff",
                because: $"every response path ({requestPath}) must carry X-Content-Type-Options: nosniff");
    }
}
