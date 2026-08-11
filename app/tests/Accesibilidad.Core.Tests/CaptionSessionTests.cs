using Accesibilidad.Core;

namespace Accesibilidad.Core.Tests;

/// <summary>
/// La sesión es lo que convierte el sistema en multiusuario: un emisor (el docente) y
/// muchos receptores (los alumnos). Si la difusión falla, cada alumno ve una pantalla
/// vacía sin que nada dé error — el emisor seguiría funcionando perfectamente.
/// </summary>
public class CaptionSessionTests
{
    private static TranscriptSegment Segment(long seq, string texto) =>
        new(seq, texto, false, [], DateTimeOffset.UtcNow, DateTimeOffset.UtcNow);

    [Fact]
    public void PublicarLlegaATodosLosReceptores()
    {
        var sesion = new CaptionSession();
        var alumnoA = new List<string>();
        var alumnoB = new List<string>();
        sesion.SegmentPublished += s => alumnoA.Add(s.Text);
        sesion.SegmentPublished += s => alumnoB.Add(s.Text);

        sesion.Start(new Glossary([]));
        sesion.Publish(Segment(0, "hola clase"));

        Assert.Equal(["hola clase"], alumnoA);
        Assert.Equal(["hola clase"], alumnoB);
    }

    [Fact]
    public void QuienLlegaTardeRecuperaElHistorial()
    {
        var sesion = new CaptionSession();
        sesion.Start(new Glossary([]));
        sesion.Publish(Segment(0, "primera frase"));
        sesion.Publish(Segment(1, "segunda frase"));

        // Un alumno que abre la página a mitad de clase.
        var recuperado = sesion.History.Select(s => s.Text).ToArray();

        Assert.Equal(["primera frase", "segunda frase"], recuperado);
    }

    [Fact]
    public void IniciarDescartaLaEmisionAnterior()
    {
        var sesion = new CaptionSession();
        sesion.Start(new Glossary([]));
        sesion.Publish(Segment(0, "clase de ayer"));

        sesion.Start(new Glossary([]));   // clase nueva

        Assert.Empty(sesion.History);
        Assert.True(sesion.IsLive);
    }

    [Fact]
    public void ElHistorialNoCreceSinLimite()
    {
        // Una clase de una hora produce cientos de segmentos. Sin tope, la memoria del
        // servidor crecería durante toda la sesión.
        var sesion = new CaptionSession();
        sesion.Start(new Glossary([]));
        for (var i = 0; i < 600; i++) sesion.Publish(Segment(i, $"frase {i}"));

        Assert.True(sesion.History.Count <= 400);
        // Lo que se conserva es lo RECIENTE, que es lo que necesita quien llega tarde.
        Assert.Equal("frase 599", sesion.History[^1].Text);
    }

    [Fact]
    public void DetenerMarcaFinDeEmisionPeroConservaLoDicho()
    {
        var sesion = new CaptionSession();
        sesion.Start(new Glossary([]));
        sesion.Publish(Segment(0, "fin de la clase"));

        sesion.Stop();

        Assert.False(sesion.IsLive);
        // El alumno debe poder seguir leyendo lo último tras acabar la clase.
        Assert.Single(sesion.History);
    }

    [Fact]
    public void ElGlosarioDeLaSesionLlegaALosReceptores()
    {
        var sesion = new CaptionSession();
        sesion.Start(new Glossary(["mitocondria"]));

        // El receptor resalta con el glosario que fijó el docente, no con el suyo.
        var trozos = sesion.Glossary.Mark("la mitocondria produce energía");

        Assert.Contains(trozos, t => t.IsConcept && t.Text == "mitocondria");
    }

    [Fact]
    public void ReceptorQueSeDesuscribeDejaDeRecibir()
    {
        var sesion = new CaptionSession();
        var recibidos = new List<string>();
        void Manejador(TranscriptSegment s) => recibidos.Add(s.Text);

        sesion.SegmentPublished += Manejador;
        sesion.Start(new Glossary([]));
        sesion.Publish(Segment(0, "con alumno"));

        sesion.SegmentPublished -= Manejador;   // el alumno cierra la pestaña
        sesion.Publish(Segment(1, "sin alumno"));

        Assert.Equal(["con alumno"], recibidos);
    }
}
