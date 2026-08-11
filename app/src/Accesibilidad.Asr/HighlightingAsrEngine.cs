using System.Runtime.CompilerServices;
using Accesibilidad.Core;

namespace Accesibilidad.Asr;

/// <summary>
/// Envoltorio que añade detección de conceptos clave a cualquier motor ASR.
///
/// <para>
/// Es un decorador y no una funcionalidad dentro de cada motor por dos razones. Primera:
/// el resaltado es independiente de cómo se reconozca el audio, así que repetirlo en cada
/// implementación sería duplicar. Segunda, y más importante para el TFM: mantiene los
/// motores comparables entre sí. Si el resaltado viviera dentro de uno de ellos, comparar
/// dos técnicas de adaptación mezclaría dos cosas distintas.
/// </para>
/// </summary>
public sealed class HighlightingAsrEngine(IAsrEngine interno, Glossary glosario)
    : IAsrEngine, ISegmentationDiagnostics
{
    /// <summary>Reenvía al motor envuelto: sin esto, el diagnóstico se perdería aquí.</summary>
    public (int BySilence, int ByTimeout) Cuts =>
        interno is ISegmentationDiagnostics d ? d.Cuts : (0, 0);

    public string Name => $"{interno.Name} + glosario ({glosario.Terms.Count} términos)";

    public async IAsyncEnumerable<TranscriptSegment> TranscribeAsync(
        IAsyncEnumerable<AudioChunk> fragmentos,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        await foreach (var segmento in interno.TranscribeAsync(fragmentos, ct))
            yield return segmento with { KeyConcepts = glosario.Detect(segmento.Text) };
    }
}
