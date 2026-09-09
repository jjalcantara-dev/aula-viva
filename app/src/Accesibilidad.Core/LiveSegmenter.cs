namespace Accesibilidad.Core;

/// <summary>Ajustes del segmentador. Los valores por defecto vienen de exp-102.</summary>
public sealed class SegmentationOptions
{
    /// <summary>
    /// Duración máxima antes de cortar por la fuerza. Acota el peor caso.
    /// <para>
    /// 8 s es el tope de la fila ganadora de exp-102 (WER 12.48%, duración media 2.93 s,
    /// p95 5.92 s), y son esas las cifras de latencia que reporta la memoria. Conviene no
    /// leerlo como «los segmentos duran 8 s»: con corte por pausas el tope casi nunca se
    /// alcanza, de ahí que la media se quede en 2.9 s. Bajarlo a 5 s acorta el peor caso
    /// pero empeora el WER hasta 14.53%, también medido.
    /// </para>
    /// </summary>
    public double MaxSeconds { get; set; } = 8.0;

    /// <summary>Duración mínima: por debajo, el modelo se queda sin contexto acústico.</summary>
    public double MinSeconds { get; set; } = 1.5;

    /// <summary>
    /// Pausa que se considera frontera de frase. Más corta es respiración.
    /// <para>
    /// 300 ms es el valor que midió exp-102 sobre audio real (12.48% de WER, el mejor del
    /// barrido). La práctica habitual del sector usa 600 ms para dar por terminada una
    /// intervención: corta menos veces en mitad de frase, a costa de más latencia. Si el
    /// diagnóstico de la interfaz muestra cortes en mitad de sintagma, subirlo.
    /// </para>
    /// </summary>
    public double MinSilenceSeconds { get; set; } = 0.3;

    /// <summary>
    /// Fracción del nivel de voz por debajo de la cual se considera silencio.
    /// <para>
    /// El umbral se define respecto a la MEDIANA de las energías recientes, que durante
    /// el habla es el nivel de la voz. Definirlo respecto al percentil 25, como hace la
    /// versión offline donde la grabación entera sí contiene pausas, falla en vivo: si
    /// el hablante lleva unos segundos sin parar, el percentil 25 ya es voz y el sistema
    /// se cree en silencio permanente. Detectado por las pruebas.
    /// </para>
    /// <para>
    /// 0.35 es el valor validado en exp-102. Requiere que el control automático de
    /// ganancia del navegador esté DESACTIVADO: con AGC, al callar el hablante la
    /// ganancia sube, el ruido de fondo se amplifica y la energía nunca baja lo
    /// suficiente. Medido en uso real, con AGC activo prácticamente todos los segmentos
    /// se cerraban por agotar el tope en lugar de por pausa.
    /// </para>
    /// </summary>
    public double SilenceFactor { get; set; } = 0.35;
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
public sealed class LiveSegmenter(int frecuencia, SegmentationOptions? opciones = null)
{
    private const int MsPorTrama = 20;
    /// <summary>Tramas recientes para estimar el nivel de fondo (unos 5 segundos).</summary>
    private const int TramasHistorial = 250;

    private readonly SegmentationOptions _op = opciones ?? new SegmentationOptions();
    private readonly int _muestrasPorTrama = frecuencia * MsPorTrama / 1000;
    private readonly List<byte> _acumulado = [];
    private readonly Queue<double> _historial = new();

    private int _tramasSilencioSeguidas;
    private int _restoMuestras;

    /// <summary>
    /// Proporción mínima de tramas con voz para que merezca la pena transcribir. Enviar
    /// al modelo un segmento casi vacío es lo que provoca que invente: sobre silencio,
    /// Whisper emite las frases más frecuentes de su entrenamiento.
    /// </summary>
    private const double ProporcionVozMinima = 0.15;

    private int _tramasConVoz;
    private int _tramasTotales;

    /// <summary>Segmentos descartados por no contener voz suficiente.</summary>
    public int DiscardedAsSilence { get; private set; }

    /// <summary>Segmentos cerrados al detectar una pausa. Es el comportamiento deseado.</summary>
    public int CutsBySilence { get; private set; }

    /// <summary>
    /// Segmentos cerrados por agotar el tope de duración. Si domina esta cifra, el
    /// detector de silencios NO está funcionando y el sistema se comporta como si
    /// troceara por reloj, que es justo lo que exp-102 midió como peor opción.
    /// </summary>
    public int CutsByTimeout { get; private set; }

    /// <summary>Segundos de audio acumulados sin emitir.</summary>
    public double BufferedSeconds => _acumulado.Count / 2.0 / frecuencia;

    /// <summary>
    /// Añade audio y devuelve un segmento si toca cortar, o <c>null</c> si hay que seguir
    /// acumulando.
    /// </summary>
    public byte[]? Add(ReadOnlySpan<byte> pcm)
    {
        foreach (var b in pcm) _acumulado.Add(b);

        // Analizar solo las tramas completas nuevas; el resto espera al siguiente bloque.
        var muestrasTotales = _acumulado.Count / 2;
        for (; _restoMuestras + _muestrasPorTrama <= muestrasTotales; _restoMuestras += _muestrasPorTrama)
        {
            var energia = EnergiaTrama(_restoMuestras);
            _historial.Enqueue(energia);
            if (_historial.Count > TramasHistorial) _historial.Dequeue();

            var esSilencio = energia < UmbralSilencio();
            _tramasSilencioSeguidas = esSilencio ? _tramasSilencioSeguidas + 1 : 0;
            _tramasTotales++;
            if (!esSilencio) _tramasConVoz++;
        }

        var silencioSuficiente = _tramasSilencioSeguidas * MsPorTrama / 1000.0
                                 >= _op.MinSilenceSeconds;

        // El orden importa: se comprueba la pausa ANTES que el tope, porque cuando el
        // segmento llega al tope justo durante un silencio el corte es por pausa, y
        // contarlo como tope falsearía el diagnóstico en el sentido más confuso posible.
        if (silencioSuficiente && BufferedSeconds >= _op.MinSeconds)
            return CortarSiHayVoz(porPausa: true);
        if (BufferedSeconds >= _op.MaxSeconds)
            return CortarSiHayVoz(porPausa: false);
        return null;
    }

    /// <summary>
    /// Devuelve lo que quede pendiente. Para no perder el final de una intervención.
    /// No cuenta como corte: lo provoca que se pare la captura, no el criterio de corte.
    /// </summary>
    public byte[]? Flush() => _acumulado.Count > 0 ? CortarSiHayVoz(porPausa: null) : null;

    /// <summary>
    /// Cierra el segmento, pero lo descarta si apenas contiene voz.
    ///
    /// <para>Es la PRIMERA barrera contra las alucinaciones, y actúa antes de gastar una
    /// inferencia: sobre silencio, el modelo emite las frases más frecuentes de su
    /// entrenamiento en lugar de callar. La segunda barrera, ya sobre el texto devuelto,
    /// es <see cref="HallucinationFilter"/>.</para>
    ///
    /// <para>El audio se descarta en cualquier caso: dejarlo en el búfer haría que el
    /// siguiente segmento arrastrase el silencio y volviera a dispararse el tope.</para>
    ///
    /// <para>Un descarte NO suma al reparto entre pausa y tope. Ese reparto existe para
    /// saber si el detector de silencios funciona sobre el habla del docente, y una pausa
    /// larga produce un corte cada <see cref="SegmentationOptions.MinSeconds"/>: contarlos
    /// dejaría el diagnóstico en «casi todo por pausa» precisamente cuando nadie habla,
    /// que es la lectura contraria a la que debe dar.</para>
    /// </summary>
    /// <param name="porPausa">
    /// <c>true</c> si cierra una pausa, <c>false</c> si cierra el tope, <c>null</c> si es
    /// el vaciado final, que no responde a ningún criterio de corte.
    /// </param>
    private byte[]? CortarSiHayVoz(bool? porPausa)
    {
        var proporcionVoz = _tramasTotales > 0
            ? (double)_tramasConVoz / _tramasTotales
            : 0.0;
        // Sin historial suficiente el umbral es 0 y NADA se marca como silencio, de modo
        // que la proporción sale 1 y el segmento pasa. Es el comportamiento seguro al
        // arrancar: ante la duda, transcribir.
        var mudo = _tramasTotales > 0 && proporcionVoz < ProporcionVozMinima;

        var segmento = Cortar();
        if (mudo)
        {
            DiscardedAsSilence++;
            return null;
        }

        if (porPausa is true) CutsBySilence++;
        else if (porPausa is false) CutsByTimeout++;
        return segmento;
    }

    private byte[] Cortar()
    {
        var segmento = _acumulado.ToArray();
        _acumulado.Clear();
        _restoMuestras = 0;
        _tramasSilencioSeguidas = 0;
        _tramasConVoz = 0;
        _tramasTotales = 0;
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
        return ordenadas[ordenadas.Length / 2] * _op.SilenceFactor;
    }
}
