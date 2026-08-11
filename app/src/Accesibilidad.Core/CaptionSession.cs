namespace Accesibilidad.Core;

/// <summary>
/// Sesión de clase compartida: un emisor, muchos receptores.
///
/// <para><b>Topología del sistema.</b> El docente abre la página de emisión y su navegador
/// captura el micrófono. Los alumnos abren la página de recepción y <b>solo miran</b>: no
/// capturan audio, no ejecutan el modelo y no hacen ningún cálculo. Todo el reconocimiento
/// ocurre una sola vez, en el servidor.</para>
///
/// <para>Esto no es solo comodidad: es lo que hace viable el despliegue. El modelo se carga
/// una vez y transcribe una vez, con independencia de que la clase tenga tres alumnos o
/// treinta. Un diseño donde cada cliente transcribiera necesitaría una GPU por alumno.</para>
///
/// <para>Como todos los clientes son circuitos de Blazor Server sobre el mismo proceso,
/// la difusión se resuelve en memoria. No hace falta un hub de SignalR aparte: Blazor ya
/// mantiene un websocket con cada cliente y por ahí viajan las actualizaciones.</para>
/// </summary>
public sealed class CaptionSession
{
    private readonly object _cerrojo = new();
    private readonly List<TranscriptSegment> _historial = [];

    /// <summary>Se dispara al publicar un segmento nuevo. Lo escuchan los receptores.</summary>
    public event Action<TranscriptSegment>? SegmentPublished;

    /// <summary>Se dispara al empezar o terminar una emisión, para que los receptores se refresquen.</summary>
    public event Action? StateChanged;

    /// <summary>Hay una emisión activa.</summary>
    public bool IsLive { get; private set; }

    /// <summary>Glossary de la sesión, fijado por el docente al empezar.</summary>
    public Glossary Glossary { get; private set; } = new([]);

    /// <summary>Instante de inicio de la emisión en curso.</summary>
    public DateTimeOffset? StartedAt { get; private set; }

    /// <summary>Copia del historial. Un receptor que llega tarde ve lo ya dicho.</summary>
    public IReadOnlyList<TranscriptSegment> History
    {
        get { lock (_cerrojo) return _historial.ToArray(); }
    }

    public void Start(Glossary glosario)
    {
        lock (_cerrojo)
        {
            _historial.Clear();
            Glossary = glosario;
            IsLive = true;
            StartedAt = DateTimeOffset.UtcNow;
        }
        StateChanged?.Invoke();
    }

    public void Publish(TranscriptSegment segmento)
    {
        lock (_cerrojo)
        {
            _historial.Add(segmento);
            // El historial no crece sin límite: una clase de una hora son cientos de
            // segmentos y un receptor que entra tarde no necesita toda la sesión.
            if (_historial.Count > 400) _historial.RemoveRange(0, 100);
        }
        SegmentPublished?.Invoke(segmento);
    }

    public void Stop()
    {
        lock (_cerrojo) IsLive = false;
        StateChanged?.Invoke();
    }
}
