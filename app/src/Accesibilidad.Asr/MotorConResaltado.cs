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
public sealed class MotorConResaltado(IMotorAsr interno, Glosario glosario) : IMotorAsr
{
    public string Nombre => $"{interno.Nombre} + glosario ({glosario.Terminos.Count} términos)";

    public async IAsyncEnumerable<SegmentoTranscrito> TranscribirAsync(
        IAsyncEnumerable<FragmentoAudio> fragmentos,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        await foreach (var segmento in interno.TranscribirAsync(fragmentos, ct))
            yield return segmento with { ConceptosClave = glosario.Detectar(segmento.Texto) };
    }
}
