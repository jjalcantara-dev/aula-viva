using Accesibilidad.Asr;
using Accesibilidad.Core;
using Accesibilidad.Web.Components;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

// La aplicación depende de IMotorAsr, nunca de una implementación concreta. Es la
// frontera descrita en PLANNING.md: cambiar de motor no toca ni la interfaz ni la página.
//
//   Asr:Motor = "simulado"  -> mide la latencia del circuito, sin modelo
//   Asr:Motor = "whisper"   -> motor real; requiere serving/servidor_asr.py en marcha
var opciones = builder.Configuration.GetSection("Asr").Get<OpcionesWhisper>()
               ?? new OpcionesWhisper();

// Glosario de la asignatura: lo aporta el docente, no se deduce del audio.
builder.Services.AddSingleton(new Glosario(
    builder.Configuration.GetSection("Glosario:Terminos").Get<string[]>() ?? []));

if (builder.Configuration["Asr:Motor"] == "whisper")
{
    builder.Services.AddSingleton(opciones);
    builder.Services.AddHttpClient<MotorAsrWhisper>(c =>
    {
        c.BaseAddress = new Uri(opciones.Url);
        // Una ventana puede tardar en decodificar; el valor por defecto de 100 s es
        // excesivo para audio en vivo, pero cortar demasiado pronto pierde el segmento.
        c.Timeout = TimeSpan.FromSeconds(30);
    });
    builder.Services.AddScoped<IMotorAsr>(sp => new MotorConResaltado(
        sp.GetRequiredService<MotorAsrWhisper>(), sp.GetRequiredService<Glosario>()));
}
else
{
    builder.Services.AddScoped<IMotorAsr>(sp => new MotorConResaltado(
        new MotorAsrSimulado(), sp.GetRequiredService<Glosario>()));
}

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}
app.UseStatusCodePagesWithReExecute("/not-found", createScopeForStatusCodePages: true);
app.UseHttpsRedirection();

app.UseAntiforgery();

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
