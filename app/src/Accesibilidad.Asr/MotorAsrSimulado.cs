using System.Runtime.CompilerServices;
using Accesibilidad.Core;

namespace Accesibilidad.Asr;

/// <summary>
/// Motor de mentira: no reconoce nada. Devuelve texto fijo tras un retardo configurable.
///
/// Su único propósito es <b>medir la latencia del circuito vacío</b> — micrófono, red,
/// servidor, render — sin la contribución del modelo. Ese número es el presupuesto real
/// del que se dispone antes de meter el ASR: si el circuito vacío ya consume medio
/// segundo, el modelo no puede gastar más que la diferencia.
///
/// El barrido de M0 midió <c>large-v3-turbo</c> a ~20x más rápido que el audio, así que
/// se espera que el cuello de botella esté aquí y no en el modelo.
/// </summary>
public sealed class MotorAsrSimulado : IMotorAsr
{
    private static readonly string[] TextoFalso =
    [
        "esto es una transcripción simulada",
        "el motor real todavía no está conectado",
        "sirve para medir la latencia del circuito",
    ];

    private readonly TimeSpan _retardoSimulado;

    /// <param name="retardoSimulado">
    /// Retardo artificial por fragmento. Cero mide el circuito puro; valores mayores
    /// permiten comprobar cómo se degrada la interfaz cuando el modelo va justo.
    /// </param>
    public MotorAsrSimulado(TimeSpan? retardoSimulado = null) =>
        _retardoSimulado = retardoSimulado ?? TimeSpan.Zero;

    public string Nombre => _retardoSimulado == TimeSpan.Zero
        ? "simulado (circuito vacío)"
        : $"simulado (+{_retardoSimulado.TotalMilliseconds:F0} ms)";

    public async IAsyncEnumerable<SegmentoTranscrito> TranscribirAsync(
        IAsyncEnumerable<FragmentoAudio> fragmentos,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        await foreach (var fragmento in fragmentos.WithCancellation(ct))
        {
            if (_retardoSimulado > TimeSpan.Zero)
                await Task.Delay(_retardoSimulado, ct);

            yield return new SegmentoTranscrito(
                Secuencia: fragmento.Secuencia,
                Texto: TextoFalso[(int)(fragmento.Secuencia % TextoFalso.Length)],
                EsParcial: false,
                ConceptosClave: [],
                CapturadoEn: fragmento.CapturadoEn,
                TranscritoEn: DateTimeOffset.UtcNow);
        }
    }
}
