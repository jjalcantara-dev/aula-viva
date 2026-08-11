namespace Accesibilidad.Core;

/// <summary>
/// Fragmento de audio capturado del micrófono, ya en el formato que espera un
/// motor ASR: PCM 16 bits, mono.
/// </summary>
/// <param name="Sequence">Orden de captura. Permite detectar fragmentos perdidos.</param>
/// <param name="Samples">PCM 16 bits con signo, little-endian, mono.</param>
/// <param name="SampleRate">Hz. Whisper trabaja a 16000.</param>
/// <param name="CapturedAt">
/// Instante de captura en el servidor. Es el origen de la medida de latencia:
/// sin él, "tiempo real" no se puede verificar y queda como afirmación indefendible.
/// </param>
public readonly record struct AudioChunk(
    long Sequence,
    ReadOnlyMemory<byte> Samples,
    int SampleRate,
    DateTimeOffset CapturedAt)
{
    /// <summary>Duración del fragmento, derivada del tamaño y la frecuencia.</summary>
    public TimeSpan Duration =>
        TimeSpan.FromSeconds(Samples.Length / 2.0 / SampleRate);
}

/// <summary>Text reconocido correspondiente a uno o varios fragmentos.</summary>
/// <param name="IsPartial">
/// Una hipótesis parcial puede corregirse cuando llegue más audio. La interfaz debe
/// distinguirlas visualmente: en accesibilidad, un subtítulo que cambia sin avisar
/// desorienta más que un subtítulo que llega medio segundo más tarde.
/// </param>
/// <param name="KeyConcepts">
/// Términos a resaltar. En la versión mínima proceden de un glosario por asignatura;
/// la detección semántica es alcance opcional (ver PLANNING, punto de recorte 1).
/// </param>
public readonly record struct TranscriptSegment(
    long Sequence,
    string Text,
    bool IsPartial,
    IReadOnlyList<string> KeyConcepts,
    DateTimeOffset CapturedAt,
    DateTimeOffset TranscribedAt)
{
    /// <summary>Latency de extremo a extremo. La métrica que decide si esto sirve en un aula.</summary>
    public TimeSpan Latency => TranscribedAt - CapturedAt;
}

/// <summary>
/// LA FRONTERA entre el núcleo aplicado y el núcleo investigador.
///
/// La aplicación depende solo de esta interfaz, nunca del código de <c>research/</c>.
/// Eso permite (a) enseñar una demo con el modelo base mientras la comparativa sigue en
/// curso, y (b) sustituir la técnica ganadora al final sin tocar la aplicación.
/// </summary>
public interface IAsrEngine
{
    /// <summary>Identificador de la configuración en uso. Debe aparecer en la UI y en los registros.</summary>
    string Name { get; }

    /// <summary>
    /// Consume audio y emite transcripciones a medida que están disponibles. Es un flujo,
    /// no una petición-respuesta: un motor real emite hipótesis parciales antes de cerrar
    /// un segmento.
    /// </summary>
    IAsyncEnumerable<TranscriptSegment> TranscribeAsync(
        IAsyncEnumerable<AudioChunk> fragmentos,
        CancellationToken ct = default);
}
