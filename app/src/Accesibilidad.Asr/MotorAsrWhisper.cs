using System.Buffers;
using System.Net.Http.Json;
using System.Runtime.CompilerServices;
using System.Text.Json.Serialization;
using Accesibilidad.Core;

namespace Accesibilidad.Asr;

/// <summary>Ajustes del motor real. Los valores por defecto son un punto de partida, no un óptimo.</summary>
public sealed class OpcionesWhisper
{
    /// <summary>URL del servicio Python (<c>serving/servidor_asr.py</c>).</summary>
    public string Url { get; set; } = "http://localhost:5601";

    /// <summary>
    /// Cómo se decide dónde cortar el audio. Por defecto, en los silencios.
    /// <para>
    /// exp-102: cortando en pausas en vez de por reloj, el WER baja 7.4 puntos a igual
    /// latencia media. exp-103 descartó además arrastrar contexto entre segmentos: no
    /// aporta y propaga errores.
    /// </para>
    /// </summary>
    public OpcionesSegmentacion Segmentacion { get; set; } = new();

    /// <summary>Glosario opcional del dominio, como prompt contextual (técnica de exp-001).</summary>
    public string? Prompt { get; set; }
}

/// <summary>
/// Motor real: acumula audio hasta encontrar una pausa y envía el segmento al servicio
/// Python. El corte lo decide <see cref="SegmentadorEnVivo"/>.
///
/// <para><b>Limitaciones conocidas</b>:</para>
/// <list type="bullet">
/// <item>No emite hipótesis parciales: cada segmento se publica cerrado.</item>
/// <item>El detector de silencios es de energía, no entrenado. Con ruido de aula real
/// puede fallar; un VAD entrenado sería más robusto (ver exp-102).</item>
/// <item>Sin difusión a varios receptores: haría falta un hub de SignalR dedicado.</item>
/// </list>
/// </summary>
public sealed class MotorAsrWhisper : IMotorAsr
{
    private sealed record Respuesta(
        [property: JsonPropertyName("texto")] string Texto,
        [property: JsonPropertyName("ms_inferencia")] double MsInferencia);

    private readonly HttpClient _http;
    private readonly OpcionesWhisper _opciones;

    public MotorAsrWhisper(HttpClient http, OpcionesWhisper opciones)
    {
        _http = http;
        _opciones = opciones;
        _http.BaseAddress ??= new Uri(opciones.Url);
    }

    public string Nombre => $"Whisper vía {_opciones.Url} " +
                            $"(corte por silencios, máx {_opciones.Segmentacion.MaximoSegundos:0.#}s)";

    public async IAsyncEnumerable<SegmentoTranscrito> TranscribirAsync(
        IAsyncEnumerable<FragmentoAudio> fragmentos,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        var frecuencia = 16_000;
        DateTimeOffset? inicioVentana = null;
        var anterior = string.Empty;

        // Secuencia del PRIMER fragmento que compone la ventana actual, no un contador
        // propio de segmentos. El cliente mide la latencia emparejando el subtítulo con
        // el instante en que envió ese fragmento; si el motor numerase sus propios
        // segmentos, el desfase crecería con cada ventana y la latencia medida sería
        // pura ficción.
        long? secuenciaInicial = null;

        SegmentadorEnVivo? segmentador = null;

        await foreach (var fragmento in fragmentos.WithCancellation(ct))
        {
            frecuencia = fragmento.FrecuenciaMuestreo;
            segmentador ??= new SegmentadorEnVivo(frecuencia, _opciones.Segmentacion);
            inicioVentana ??= fragmento.CapturadoEn;
            secuenciaInicial ??= fragmento.Secuencia;

            var segmento = segmentador.Añadir(fragmento.Muestras.Span);
            if (segmento is null)
                continue;   // aún no hay pausa ni se ha alcanzado el tope

            var crudo = await EnviarAsync(segmento, frecuencia, ct);

            // Los cortes caen en silencio, así que no debería haber solape; se mantiene
            // la deduplicación como red de seguridad ante cortes forzados por el tope.
            var texto = Solapamiento.Fusionar(anterior, crudo);
            if (!string.IsNullOrWhiteSpace(crudo)) anterior = crudo;

            if (!string.IsNullOrWhiteSpace(texto))
            {
                yield return new SegmentoTranscrito(
                    Secuencia: secuenciaInicial.Value,
                    Texto: texto,
                    EsParcial: false,
                    ConceptosClave: [],
                    CapturadoEn: inicioVentana.Value,
                    TranscritoEn: DateTimeOffset.UtcNow);
            }

            inicioVentana = null;
            secuenciaInicial = null;
        }

        // Cola final: no descartar el último medio segundo de una intervención.
        if (segmentador?.Vaciar() is { } resto && inicioVentana is { } inicio)
        {
            var texto = Solapamiento.Fusionar(
                anterior, await EnviarAsync(resto, frecuencia, ct));
            if (!string.IsNullOrWhiteSpace(texto))
            {
                yield return new SegmentoTranscrito(
                    secuenciaInicial ?? 0, texto, false, [], inicio, DateTimeOffset.UtcNow);
            }
        }
    }

    private async Task<string> EnviarAsync(byte[] pcm, int frecuencia, CancellationToken ct)
    {
        using var contenido = new ByteArrayContent(pcm);
        contenido.Headers.Add("X-Frecuencia", frecuencia.ToString());
        if (!string.IsNullOrWhiteSpace(_opciones.Prompt))
            contenido.Headers.Add("X-Prompt", _opciones.Prompt);

        using var respuesta = await _http.PostAsync("/transcribir", contenido, ct);
        respuesta.EnsureSuccessStatusCode();
        var cuerpo = await respuesta.Content.ReadFromJsonAsync<Respuesta>(ct);
        return cuerpo?.Texto ?? string.Empty;
    }
}
