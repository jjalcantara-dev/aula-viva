using System.Buffers;
using System.Net.Http.Json;
using System.Runtime.CompilerServices;
using System.Text.Json.Serialization;
using Accesibilidad.Core;

namespace Accesibilidad.Asr;

/// <summary>Ajustes del motor real. Los valores por defecto son un punto de partida, no un óptimo.</summary>
public sealed class WhisperOptions
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
    public SegmentationOptions Segmentation { get; set; } = new();

    /// <summary>Glossary opcional del dominio, como prompt contextual (técnica de exp-001).</summary>
    public string? Prompt { get; set; }
}

/// <summary>
/// Motor real: acumula audio hasta encontrar una pausa y envía el segmento al servicio
/// Python. El corte lo decide <see cref="LiveSegmenter"/>.
///
/// <para><b>Limitaciones conocidas</b>:</para>
/// <list type="bullet">
/// <item>No emite hipótesis parciales: cada segmento se publica cerrado.</item>
/// <item>El detector de silencios es de energía, no entrenado. Con ruido de aula real
/// puede fallar; un VAD entrenado sería más robusto (ver exp-102).</item>
/// <item>Sin difusión a varios receptores: haría falta un hub de SignalR dedicado.</item>
/// </list>
/// </summary>
public sealed class WhisperAsrEngine : IAsrEngine, ISegmentationDiagnostics
{
    private sealed record Respuesta(
        [property: JsonPropertyName("texto")] string Text,
        [property: JsonPropertyName("ms_inferencia")] double MsInferencia);

    private readonly HttpClient _http;
    private readonly WhisperOptions _opciones;
    private LiveSegmenter? _ultimoSegmentador;

    /// <summary>Transcripciones descartadas por parecer inventadas.</summary>
    public int Descartadas { get; private set; }

    /// <summary>Último descarte, para poder mostrarlo en la interfaz.</summary>
    public string? UltimoDescarte { get; private set; }

    public (int BySilence, int ByTimeout) Cuts =>
        (_ultimoSegmentador?.CutsBySilence ?? 0, _ultimoSegmentador?.CutsByTimeout ?? 0);

    public WhisperAsrEngine(HttpClient http, WhisperOptions opciones)
    {
        _http = http;
        _opciones = opciones;
        _http.BaseAddress ??= new Uri(opciones.Url);
    }

    public string Name => $"Whisper vía {_opciones.Url} " +
                            $"(corte por silencios, máx {_opciones.Segmentation.MaxSeconds:0.#}s)";

    public async IAsyncEnumerable<TranscriptSegment> TranscribeAsync(
        IAsyncEnumerable<AudioChunk> fragmentos,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        var frecuencia = 16_000;
        DateTimeOffset? inicioVentana = null;
        var anterior = string.Empty;

        // Sequence del PRIMER fragmento que compone la ventana actual, no un contador
        // propio de segmentos. El cliente mide la latencia emparejando el subtítulo con
        // el instante en que envió ese fragmento; si el motor numerase sus propios
        // segmentos, el desfase crecería con cada ventana y la latencia medida sería
        // pura ficción.
        long? secuenciaInicial = null;

        LiveSegmenter? segmentador = null;

        await foreach (var fragmento in fragmentos.WithCancellation(ct))
        {
            frecuencia = fragmento.SampleRate;
            segmentador ??= _ultimoSegmentador = new LiveSegmenter(frecuencia, _opciones.Segmentation);
            inicioVentana ??= fragmento.CapturedAt;
            secuenciaInicial ??= fragmento.Sequence;

            var segmento = segmentador.Add(fragmento.Samples.Span);
            if (segmento is null)
                continue;   // aún no hay pausa ni se ha alcanzado el tope

            var crudo = await EnviarAsync(segmento, frecuencia, ct);

            // Segunda barrera: aunque el segmento tuviera voz, el modelo puede emitir una
            // muletilla de su entrenamiento o entrar en bucle. Descartarlo es preferible a
            // mostrar al alumno algo que nadie dijo.
            if (HallucinationFilter.Motivo(crudo) is { } motivo)
            {
                Descartadas++;
                UltimoDescarte = $"{motivo}: «{crudo.Trim()}»";
                inicioVentana = null;
                secuenciaInicial = null;
                continue;
            }

            // Los cortes caen en silencio, así que no debería haber solape; se mantiene
            // la deduplicación como red de seguridad ante cortes forzados por el tope.
            var texto = OverlapMerger.Merge(anterior, crudo);
            if (!string.IsNullOrWhiteSpace(crudo)) anterior = crudo;

            if (!string.IsNullOrWhiteSpace(texto))
            {
                yield return new TranscriptSegment(
                    Sequence: secuenciaInicial.Value,
                    Text: texto,
                    IsPartial: false,
                    KeyConcepts: [],
                    CapturedAt: inicioVentana.Value,
                    TranscribedAt: DateTimeOffset.UtcNow);
            }

            inicioVentana = null;
            secuenciaInicial = null;
        }

        // Cola final: no descartar el último medio segundo de una intervención.
        if (segmentador?.Flush() is { } resto && inicioVentana is { } inicio)
        {
            var texto = OverlapMerger.Merge(
                anterior, await EnviarAsync(resto, frecuencia, ct));
            if (!string.IsNullOrWhiteSpace(texto))
            {
                yield return new TranscriptSegment(
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
        return cuerpo?.Text ?? string.Empty;
    }
}
