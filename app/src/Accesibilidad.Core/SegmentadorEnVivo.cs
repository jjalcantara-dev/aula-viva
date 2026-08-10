namespace Accesibilidad.Core;

/// <summary>Ajustes del segmentador. Los valores por defecto vienen de exp-102.</summary>
public sealed class OpcionesSegmentacion
{
    /// <summary>Duración máxima antes de cortar por la fuerza. Acota el peor caso.</summary>
    public double MaximoSegundos { get; set; } = 8.0;

    /// <summary>Duración mínima: por debajo, el modelo se queda sin contexto acústico.</summary>
    public double MinimoSegundos { get; set; } = 1.5;

    /// <summary>Pausa que se considera frontera de frase. Más corta es respiración.</summary>
    public double SilencioMinimoSegundos { get; set; } = 0.3;

    /// <summary>
    /// Fracción del nivel de voz por debajo de la cual se considera silencio.
    /// <para>
    /// El umbral se define respecto a la MEDIANA de las energías recientes, que durante
    /// el habla es el nivel de la voz. Definirlo respecto al percentil 25 —como hace la
    /// versión offline, donde la grabación entera sí contiene pausas— falla en vivo: si
    /// el hablante lleva unos segundos sin parar, el percentil 25 ya es voz y el sistema
    /// se cree en silencio permanente. Detectado por las pruebas.
    /// </para>
    /// </summary>
    public double FactorSilencio { get; set; } = 0.35;
}

/// <summary>
/// Decide dónde cortar el audio en vivo, buscando pausas en lugar de trocear por reloj.
///
/// <para><b>Por qué.</b> exp-102 midió que cortar cada N segundos parte palabras y frases
/// justo donde el modelo más necesita contexto. Segmentando por silencios, con la misma
/// latencia media, el WER baja <b>7.4 puntos</b> (19.85% → 12.48%) y además los segmentos
/// salen más cortos, porque las pausas naturales llegan antes que el tope.</para>
///
/// <para><b>La diferencia con el experimento</b> es que aquí no se puede analizar la
/// grabación entera: el audio llega a trozos y hay que decidir sobre la marcha. El umbral
/// de silencio se estima con una ventana deslizante de energías recientes, así que se
/// adapta solo al ruido de la sala — el nivel de fondo de un aula no es el de un estudio,
/// y puede cambiar durante la clase.</para>
/// </summary>
public sealed class SegmentadorEnVivo(int frecuencia, OpcionesSegmentacion? opciones = null)
{
    private const int MsPorTrama = 20;
    /// <summary>Tramas recientes para estimar el nivel de fondo (unos 5 segundos).</summary>
    private const int TramasHistorial = 250;

    private readonly OpcionesSegmentacion _op = opciones ?? new OpcionesSegmentacion();
    private readonly int _muestrasPorTrama = frecuencia * MsPorTrama / 1000;
    private readonly List<byte> _acumulado = [];
    private readonly Queue<double> _historial = new();

    private int _tramasSilencioSeguidas;
    private int _restoMuestras;

    /// <summary>Segundos de audio acumulados sin emitir.</summary>
    public double SegundosAcumulados => _acumulado.Count / 2.0 / frecuencia;

    /// <summary>
    /// Añade audio y devuelve un segmento si toca cortar, o <c>null</c> si hay que seguir
    /// acumulando.
    /// </summary>
    public byte[]? Añadir(ReadOnlySpan<byte> pcm)
    {
        foreach (var b in pcm) _acumulado.Add(b);

        // Analizar solo las tramas completas nuevas; el resto espera al siguiente bloque.
        var muestrasTotales = _acumulado.Count / 2;
        for (; _restoMuestras + _muestrasPorTrama <= muestrasTotales; _restoMuestras += _muestrasPorTrama)
        {
            var energia = EnergiaTrama(_restoMuestras);
            _historial.Enqueue(energia);
            if (_historial.Count > TramasHistorial) _historial.Dequeue();

            _tramasSilencioSeguidas = energia < UmbralSilencio() ? _tramasSilencioSeguidas + 1 : 0;
        }

        var silencioSuficiente = _tramasSilencioSeguidas * MsPorTrama / 1000.0
                                 >= _op.SilencioMinimoSegundos;

        if (SegundosAcumulados >= _op.MaximoSegundos ||
            (silencioSuficiente && SegundosAcumulados >= _op.MinimoSegundos))
        {
            return Cortar();
        }
        return null;
    }

    /// <summary>Devuelve lo que quede pendiente. Para no perder el final de una intervención.</summary>
    public byte[]? Vaciar() => _acumulado.Count > 0 ? Cortar() : null;

    private byte[] Cortar()
    {
        var segmento = _acumulado.ToArray();
        _acumulado.Clear();
        _restoMuestras = 0;
        _tramasSilencioSeguidas = 0;
        // El historial NO se reinicia: el nivel de ruido de la sala es continuo y
        // reestimarlo desde cero en cada corte daría umbrales erráticos.
        return segmento;
    }

    private double EnergiaTrama(int primeraMuestra)
    {
        double suma = 0;
        for (var i = 0; i < _muestrasPorTrama; i++)
        {
            var b = (primeraMuestra + i) * 2;
            var muestra = (short)(_acumulado[b] | (_acumulado[b + 1] << 8)) / 32768.0;
            suma += muestra * muestra;
        }
        return Math.Sqrt(suma / _muestrasPorTrama);
    }

    /// <summary>
    /// Umbral adaptativo, relativo al nivel de voz reciente (la mediana). Mientras no
    /// haya historial suficiente devuelve 0: nada se considera silencio y el corte lo
    /// decide el tope de duración, que es el comportamiento seguro al arrancar.
    /// </summary>
    private double UmbralSilencio()
    {
        if (_historial.Count < TramasHistorial / 5) return 0;
        var ordenadas = _historial.Order().ToArray();
        return ordenadas[ordenadas.Length / 2] * _op.FactorSilencio;
    }
}
