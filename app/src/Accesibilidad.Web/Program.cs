using Accesibilidad.Asr;
using Accesibilidad.Core;
using Accesibilidad.Web.Components;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents(opciones =>
    {
        // Lotes de render pendientes de confirmar. Los subtítulos se empujan a todos los
        // clientes a la vez y un receptor lento no debe frenar al resto ni tirar su
        // circuito; 10 da holgura para un aula sin permitir que la cola crezca sin fin.
        opciones.MaxBufferedUnacknowledgedRenderBatches = 10;
    })
    .AddHubOptions(hub =>
    {
        // ESTE es el límite que afecta a la captura, y no el de arriba. El audio viaja
        // por el mismo websocket que usa Blazor para la interfaz, y el máximo por mensaje
        // que trae SignalR de serie son 32 KB. Un fragmento de 500 ms a 16 kHz en PCM de
        // 16 bits ocupa 16 KB: entra por los pelos, con factor 2. Subir MsPorFragmento a
        // 1 s con el valor de serie rompería la captura con un error de conexión que no
        // apunta al tamaño del mensaje. 128 KB deja margen hasta 4 s por fragmento.
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
// llega a ejecutarse nada más. Ver Accesibilidad.Core/LocalNetworkOnly.cs para el motivo,
// que es que difundimos audio de aula, y por qué no basta con no abrir el puerto del
// router.
//
// PRECONDICIÓN: se comprueba la IP de la conexión, sin UseForwardedHeaders. Es correcto
// en el despliegue documentado, donde los contenedores comparten la red del anfitrión y
// esa IP es la del cliente real. Detrás de un proxy inverso la comprobación vería siempre
// la del proxy y dejaría pasar cualquier origen: si algún día se pone uno delante, hay
// que configurar las cabeceras reenviadas ANTES de este middleware.
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

// Señal de vida para el orquestador de contenedores. Va DESPUES del filtro de red local a
// propósito: la comprobación llega por bucle local, que es rango privado, así que pasa; y
// que no tenga excepción propia evita abrir un hueco en la única barrera del sistema.
//
// Devuelve el motor en uso, no solo un "ok": si la aplicación arranca con el motor
// simulado en un despliegue real, el contenedor estaría sano y los subtítulos serían
// inventados. Es barato hacerlo visible aquí.
app.MapGet("/salud", (IServiceProvider sp) => Results.Ok(new
{
    estado = "vivo",
    motor = sp.CreateScope().ServiceProvider.GetRequiredService<IAsrEngine>().Name,
}));

app.UseStatusCodePagesWithReExecute("/not-found", createScopeForStatusCodePages: true);

app.UseAntiforgery();

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
