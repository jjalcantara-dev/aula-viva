namespace Accesibilidad.Core;

/// <summary>
/// Diagnóstico de la segmentación, separado de <see cref="IAsrEngine"/>.
///
/// <para>Va aparte por dos razones. Primera: no todos los motores segmentan —el simulado
/// no—, así que meterlo en el contrato principal obligaría a implementaciones vacías.
/// Segunda, y más importante: los motores se componen por decoración
/// (<c>HighlightingAsrEngine</c> envuelve al real), de modo que quien recibe
/// <c>IAsrEngine</c> nunca ve el tipo concreto. Un <c>is WhisperAsrEngine</c> desde la
/// interfaz siempre falla, y el diagnóstico saldría vacío sin que nada lo delate.</para>
///
/// <para>Con esta interfaz, cada decorador reenvía la consulta al motor que envuelve.</para>
/// </summary>
public interface ISegmentationDiagnostics
{
    /// <summary>
    /// Segmentos cerrados al detectar una pausa frente a los cerrados por agotar el tope.
    /// Si domina el segundo, el detector de silencios no está encontrando las pausas y el
    /// sistema degenera en troceado por reloj — la peor opción según exp-102.
    /// </summary>
    (int BySilence, int ByTimeout) Cuts { get; }
}
