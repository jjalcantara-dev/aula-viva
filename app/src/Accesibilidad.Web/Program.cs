using Accesibilidad.Asr;
using Accesibilidad.Core;
using Accesibilidad.Web.Components;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents(opciones =>
    {
        // El audio viaja por el mismo websocket que usa Blazor para la interfaz, y el
        // límite por defecto de SignalR son 32 KB por mensaje. Un fragmento de 500 ms a
        // 16 kHz en PCM de 16 bits ocupa 16 KB: entra por los pelos, con factor 2. Subir
        // MsPorFragmento a 1 s rompería la captura con un error de conexión poco
        // descriptivo, sin que nada apunte al tamaño del mensaje.
        opciones.MaxBufferedUnacknowledgedRenderBatches = 10;
    })
    .AddHubOptions(hub =>
    {
        // 128 KB deja margen para fragmentos de hasta 4 s.
        hub.MaximumReceiveMessageSize = 128 * 1024;
    });

// La aplicación depende de IAsrEngine, nunca de una implementación concreta. Es la
// frontera descrita en PLANNING.md: cambiar de motor no toca ni la interfaz ni la página.
//
//   Asr:Motor = "simulado"  -> mide la latencia del circuito, sin modelo
//   Asr:Motor = "whisper"   -> motor real; requiere serving/servidor_asr.py en marcha
var opciones = builder.Configuration.GetSection("Asr").Get<WhisperOptions>()
               ?? new WhisperOptions();

// Sesión de aula: UN emisor (el docente) y MUCHOS receptores (los alumnos). Singleton
// porque representa la clase en curso, compartida por todos los circuitos conectados.
builder.Services.AddSingleton<CaptionSession>();

// Clave del puesto docente. Sin ella la emisión queda abierta (modo desarrollo) y la
// interfaz lo advierte.
builder.Services.AddSingleton(new TeacherAccess(builder.Configuration["Aula:ClaveDocente"]));

// Glossary de la asignatura: lo aporta el docente, no se deduce del audio.
builder.Services.AddSingleton(new Glossary(
    builder.Configuration.GetSection("Glossary:Terms").Get<string[]>() ?? []));

if (builder.Configuration["Asr:Motor"] == "whisper")
{
    builder.Services.AddSingleton(opciones);
    builder.Services.AddHttpClient<WhisperAsrEngine>(c =>
    {
        c.BaseAddress = new Uri(opciones.Url);
        // Una ventana puede tardar en decodificar; el valor por defecto de 100 s es
        // excesivo para audio en vivo, pero cortar demasiado pronto pierde el segmento.
        c.Timeout = TimeSpan.FromSeconds(30);
    });
    builder.Services.AddScoped<IAsrEngine>(sp => new HighlightingAsrEngine(
        sp.GetRequiredService<WhisperAsrEngine>(), sp.GetRequiredService<Glossary>()));
}
else
{
    builder.Services.AddScoped<IAsrEngine>(sp => new HighlightingAsrEngine(
        new FakeAsrEngine(), sp.GetRequiredService<Glossary>()));
}

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}
// Solo red local. Va ANTES que nada: si la petición no viene de una red privada, no
// llega a ejecutarse nada más. Ver Accesibilidad.Core/LocalNetworkOnly.cs para el motivo
// —difundimos audio de aula— y por qué no basta con no abrir el puerto del router.
if (builder.Configuration.GetValue("Aula:SoloRedLocal", true))
{
    app.Use(async (contexto, siguiente) =>
    {
        if (!LocalNetworkOnly.IsPrivate(contexto.Connection.RemoteIpAddress))
        {
            contexto.Response.StatusCode = StatusCodes.Status403Forbidden;
            await contexto.Response.WriteAsync(
                "Este sistema solo es accesible desde la red local del centro.");
            return;
        }
        await siguiente();
    });
}

app.UseStatusCodePagesWithReExecute("/not-found", createScopeForStatusCodePages: true);

app.UseAntiforgery();

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
