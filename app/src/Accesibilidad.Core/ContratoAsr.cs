namespace Accesibilidad.Core;

/// <summary>
/// Fragmento de audio capturado del micrófono, ya en el formato que espera un
/// motor ASR: PCM 16 bits, mono.
/// </summary>
/// <param name="Secuencia">Orden de captura. Permite detectar fragmentos perdidos.</param>
/// <param name="Muestras">PCM 16 bits con signo, little-endian, mono.</param>
/// <param name="FrecuenciaMuestreo">Hz. Whisper trabaja a 16000.</param>
/// <param name="CapturadoEn">
/// Instante de captura en el servidor. Es el origen de la medida de latencia:
/// sin él, "tiempo real" no se puede verificar y queda como afirmación indefendible.
/// </param>
public readonly record struct FragmentoAudio(
    long Secuencia,
    ReadOnlyMemory<byte> Muestras,
    int FrecuenciaMuestreo,
    DateTimeOffset CapturadoEn)
{
    /// <summary>Duración del fragmento, derivada del tamaño y la frecuencia.</summary>
    public TimeSpan Duracion =>
        TimeSpan.FromSeconds(Muestras.Length / 2.0 / FrecuenciaMuestreo);
}

/// <summary>Texto reconocido correspondiente a uno o varios fragmentos.</summary>
/// <param name="EsParcial">
/// Una hipótesis parcial puede corregirse cuando llegue más audio. La interfaz debe
/// distinguirlas visualmente: en accesibilidad, un subtítulo que cambia sin avisar
/// desorienta más que un subtítulo que llega medio segundo más tarde.
/// </param>
/// <param name="ConceptosClave">
/// Términos a resaltar. En la versión mínima proceden de un glosario por asignatura;
/// la detección semántica es alcance opcional (ver PLANNING, punto de recorte 1).
/// </param>
public readonly record struct SegmentoTranscrito(
    long Secuencia,
    string Texto,
    bool EsParcial,
    IReadOnlyList<string> ConceptosClave,
    DateTimeOffset CapturadoEn,
    DateTimeOffset TranscritoEn)
{
    /// <summary>Latencia de extremo a extremo. La métrica que decide si esto sirve en un aula.</summary>
    public TimeSpan Latencia => TranscritoEn - CapturadoEn;
}

/// <summary>
/// LA FRONTERA entre el núcleo aplicado y el núcleo investigador.
///
/// La aplicación depende solo de esta interfaz, nunca del código de <c>research/</c>.
/// Eso permite (a) enseñar una demo con el modelo base mientras la comparativa sigue en
/// curso, y (b) sustituir la técnica ganadora al final sin tocar la aplicación.
/// </summary>
public interface IMotorAsr
{
    /// <summary>Identificador de la configuración en uso. Debe aparecer en la UI y en los registros.</summary>
    string Nombre { get; }

    /// <summary>
    /// Consume audio y emite transcripciones a medida que están disponibles. Es un flujo,
    /// no una petición-respuesta: un motor real emite hipótesis parciales antes de cerrar
    /// un segmento.
    /// </summary>
    IAsyncEnumerable<SegmentoTranscrito> TranscribirAsync(
        IAsyncEnumerable<FragmentoAudio> fragmentos,
        CancellationToken ct = default);
}
