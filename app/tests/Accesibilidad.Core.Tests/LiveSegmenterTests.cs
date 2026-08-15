using Accesibilidad.Core;

namespace Accesibilidad.Core.Tests;

/// <summary>
/// El segmentador decide dónde se parte el audio en vivo, y exp-102 midió que esa
/// decisión vale 7.4 puntos de WER. Sus casos límite (silencio al principio, tope
/// alcanzado, audio sin pausas) son fáciles de romper al tocarlo.
/// </summary>
public class LiveSegmenterTests
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
        var s = new LiveSegmenter(Frecuencia,
            new SegmentationOptions { MinSeconds = 1.5, MaxSeconds = 8 });
        // Medio segundo de silencio puro: no debe emitir, es demasiado corto.
        Assert.Null(s.Add(Audio(0.5, 0.0)));
    }

    [Fact]
    public void CortaAlAlcanzarElMaximo()
    {
        var s = new LiveSegmenter(Frecuencia,
            new SegmentationOptions { MaxSeconds = 2.0 });
        // Voz continua sin pausas: el tope es lo único que puede cortar. Acota el peor
        // caso de latencia, que es el precio de segmentar por silencios.
        Assert.Null(s.Add(Audio(1.0, 0.5)));
        var segmento = s.Add(Audio(1.2, 0.5));
        Assert.NotNull(segmento);
        Assert.True(segmento!.Length / 2.0 / Frecuencia >= 2.0);
    }

    [Fact]
    public void CortaEnLaPausaTrasVozSuficiente()
    {
        var s = new LiveSegmenter(Frecuencia,
            new SegmentationOptions { MinSeconds = 1.0, MaxSeconds = 10.0 });
        // History suficiente para que el umbral adaptativo se estabilice.
        Assert.Null(s.Add(Audio(2.0, 0.5)));
        var segmento = s.Add(Audio(0.6, 0.0));   // pausa clara
        Assert.NotNull(segmento);
    }

    [Fact]
    public void VaciarDevuelveLoPendienteYSoloUnaVez()
    {
        var s = new LiveSegmenter(Frecuencia);
        s.Add(Audio(0.4, 0.4));
        Assert.NotNull(s.Flush());
        Assert.Null(s.Flush());   // ya no queda nada
    }

    [Fact]
    public void TrasCortarSeReinicíaLaAcumulacion()
    {
        var s = new LiveSegmenter(Frecuencia,
            new SegmentationOptions { MaxSeconds = 1.0 });
        Assert.NotNull(s.Add(Audio(1.1, 0.5)));
        Assert.True(s.BufferedSeconds < 0.01);
    }

    /// <summary>
    /// El reparto entre cortes por pausa y por tope es el diagnóstico que la interfaz
    /// enseña al docente, y la única señal de que el control automático de ganancia del
    /// navegador está saboteando la detección de silencios. Estuvo devolviendo (0,0)
    /// porque los contadores se declararon y nunca se incrementaron.
    /// </summary>
    [Fact]
    public void ElCorteEnPausaSeContabilizaComoPausa()
    {
        var s = new LiveSegmenter(Frecuencia,
            new SegmentationOptions { MinSeconds = 1.0, MaxSeconds = 10.0 });
        Assert.Null(s.Add(Audio(2.0, 0.5)));
        Assert.NotNull(s.Add(Audio(0.6, 0.0)));

        Assert.Equal(1, s.CutsBySilence);
        Assert.Equal(0, s.CutsByTimeout);
    }

    [Fact]
    public void ElCorteForzadoSeContabilizaComoTope()
    {
        var s = new LiveSegmenter(Frecuencia,
            new SegmentationOptions { MinSeconds = 1.0, MaxSeconds = 2.0 });
        // Voz continua: no hay pausa que encontrar, así que solo puede cortar el tope.
        Assert.Null(s.Add(Audio(1.0, 0.5)));
        Assert.NotNull(s.Add(Audio(1.2, 0.5)));

        Assert.Equal(0, s.CutsBySilence);
        Assert.Equal(1, s.CutsByTimeout);
    }

    /// <summary>
    /// El caso que motiva la barrera: micrófono abierto y docente en pausa. Antes se
    /// enviaba el silencio al modelo, que respondía con la frase más frecuente de su
    /// entrenamiento («¡Suscríbete al canal!»). Ahora el segmento no llega a salir.
    /// </summary>
    [Fact]
    public void ElSegmentoSinVozSuficienteSeDescartaSinTranscribir()
    {
        var s = new LiveSegmenter(Frecuencia,
            new SegmentationOptions { MinSeconds = 1.0, MaxSeconds = 10.0 });

        // Primero voz, para que el umbral adaptativo tenga un nivel de referencia.
        Assert.Null(s.Add(Audio(2.0, 0.5)));
        Assert.NotNull(s.Add(Audio(0.4, 0.0)));   // cierra el segmento con habla dentro
        Assert.Equal(0, s.DiscardedAsSilence);

        var cortesAntes = s.CutsBySilence;

        // El siguiente segmento es solo silencio: se corta y NO se emite.
        Assert.Null(s.Add(Audio(1.2, 0.0)));
        Assert.Equal(1, s.DiscardedAsSilence);
        // Y el audio no se queda en el búfer: si se quedara, el siguiente segmento
        // arrastraría el silencio y volvería a dispararse el tope.
        Assert.True(s.BufferedSeconds < 0.01);
        // El descarte no cuenta como corte por pausa: si contara, una pausa larga llenaría
        // el diagnóstico de cortes «por pausa» justo cuando nadie está hablando.
        Assert.Equal(cortesAntes, s.CutsBySilence);
    }

    /// <summary>
    /// Al arrancar no hay historial, el umbral es 0 y nada se marca como silencio. La
    /// proporción de voz sale 1 y el segmento pasa: ante la duda, transcribir. Lo
    /// contrario descartaría el comienzo de cada clase.
    /// </summary>
    [Fact]
    public void AlArrancarNoDescartaPorFaltaDeHistorial()
    {
        var s = new LiveSegmenter(Frecuencia);
        s.Add(Audio(0.4, 0.0));
        Assert.NotNull(s.Flush());
        Assert.Equal(0, s.DiscardedAsSilence);
    }
}
