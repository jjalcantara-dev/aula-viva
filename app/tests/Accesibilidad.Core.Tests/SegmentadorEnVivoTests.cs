using Accesibilidad.Core;

namespace Accesibilidad.Core.Tests;

/// <summary>
/// El segmentador decide dónde se parte el audio en vivo, y exp-102 midió que esa
/// decisión vale 7.4 puntos de WER. Sus casos límite (silencio al principio, tope
/// alcanzado, audio sin pausas) son fáciles de romper al tocarlo.
/// </summary>
public class SegmentadorEnVivoTests
{
    private const int Frecuencia = 16_000;

    /// <summary>PCM 16 bits mono. <paramref name="amplitud"/> 0 es silencio digital.</summary>
    private static byte[] Audio(double segundos, double amplitud, int semilla = 7)
    {
        var n = (int)(Frecuencia * segundos);
        var datos = new byte[n * 2];
        var rnd = new Random(semilla);
        for (var i = 0; i < n; i++)
        {
            var v = (short)((rnd.NextDouble() * 2 - 1) * amplitud * short.MaxValue);
            datos[i * 2] = (byte)(v & 0xFF);
            datos[i * 2 + 1] = (byte)((v >> 8) & 0xFF);
        }
        return datos;
    }

    [Fact]
    public void NoCortaAntesDelMinimo()
    {
        var s = new SegmentadorEnVivo(Frecuencia,
            new OpcionesSegmentacion { MinimoSegundos = 1.5, MaximoSegundos = 8 });
        // Medio segundo de silencio puro: no debe emitir, es demasiado corto.
        Assert.Null(s.Añadir(Audio(0.5, 0.0)));
    }

    [Fact]
    public void CortaAlAlcanzarElMaximo()
    {
        var s = new SegmentadorEnVivo(Frecuencia,
            new OpcionesSegmentacion { MaximoSegundos = 2.0 });
        // Voz continua sin pausas: el tope es lo único que puede cortar. Acota el peor
        // caso de latencia, que es el precio de segmentar por silencios.
        Assert.Null(s.Añadir(Audio(1.0, 0.5)));
        var segmento = s.Añadir(Audio(1.2, 0.5));
        Assert.NotNull(segmento);
        Assert.True(segmento!.Length / 2.0 / Frecuencia >= 2.0);
    }

    [Fact]
    public void CortaEnLaPausaTrasVozSuficiente()
    {
        var s = new SegmentadorEnVivo(Frecuencia,
            new OpcionesSegmentacion { MinimoSegundos = 1.0, MaximoSegundos = 10.0 });
        // Historial suficiente para que el umbral adaptativo se estabilice.
        Assert.Null(s.Añadir(Audio(2.0, 0.5)));
        var segmento = s.Añadir(Audio(0.6, 0.0));   // pausa clara
        Assert.NotNull(segmento);
    }

    [Fact]
    public void VaciarDevuelveLoPendienteYSoloUnaVez()
    {
        var s = new SegmentadorEnVivo(Frecuencia);
        s.Añadir(Audio(0.4, 0.4));
        Assert.NotNull(s.Vaciar());
        Assert.Null(s.Vaciar());   // ya no queda nada
    }

    [Fact]
    public void TrasCortarSeReinicíaLaAcumulacion()
    {
        var s = new SegmentadorEnVivo(Frecuencia,
            new OpcionesSegmentacion { MaximoSegundos = 1.0 });
        Assert.NotNull(s.Añadir(Audio(1.1, 0.5)));
        Assert.True(s.SegundosAcumulados < 0.01);
    }
}
