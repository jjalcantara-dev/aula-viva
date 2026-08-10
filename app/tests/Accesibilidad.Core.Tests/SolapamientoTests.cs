using Accesibilidad.Core;

namespace Accesibilidad.Core.Tests;

/// <summary>
/// La deduplicación es crítica: exp-100 midió que, sin ella, trocear el audio con
/// solapamiento dispara el WER por encima del 100%. Son casos límite fáciles de
/// romper al tocar el código, así que conviene fijarlos.
/// </summary>
public class SolapamientoTests
{
    [Fact]
    public void SinAnterior_DevuelveElTextoCompleto()
    {
        Assert.Equal("hola qué tal", Solapamiento.Fusionar("", "hola qué tal"));
    }

    [Fact]
    public void SolapeCompleto_NoDevuelveNada()
    {
        // La ventana entera repite lo ya emitido: no hay nada nuevo que mostrar.
        Assert.Equal("", Solapamiento.Fusionar("el sistema de subtítulos", "el sistema de subtítulos"));
    }

    [Fact]
    public void SolapeParcial_DevuelveSoloLoNuevo()
    {
        var resultado = Solapamiento.Fusionar(
            "en el segundo acto del drama",
            "acto del drama llega el consejo");
        Assert.Equal("llega el consejo", resultado);
    }

    [Fact]
    public void SinSolape_DevuelveTodoElNuevo()
    {
        Assert.Equal("otra cosa distinta",
            Solapamiento.Fusionar("una frase cualquiera", "otra cosa distinta"));
    }

    [Fact]
    public void IgnoraPuntuacionYMayusculas()
    {
        // El modelo puntúa y capitaliza distinto en cada ventana; comparar en crudo
        // no detectaría el solape y el texto saldría duplicado.
        var resultado = Solapamiento.Fusionar(
            "quiero comenzar mis palabras",
            "Comenzar, mis palabras haciendo referencia");
        Assert.Equal("haciendo referencia", resultado);
    }

    [Fact]
    public void PrefiereElSolapeMasLargo()
    {
        // Solapes candidatos: "la" (1 palabra) y "de la" (2). Debe elegirse el mayor,
        // así que se conservan las dos últimas palabras del nuevo fragmento.
        var resultado = Solapamiento.Fusionar(
            "esto es la prueba de la",
            "de la prueba final");
        Assert.Equal("prueba final", resultado);
    }

    [Fact]
    public void NuevoVacio_DevuelveVacio()
    {
        Assert.Equal("", Solapamiento.Fusionar("algo previo", "   "));
    }

    [Fact]
    public void ToleraUnaPalabraDistintaEnLaFrontera()
    {
        // Caso real medido con micrófono: en la frontera entre ventanas el modelo
        // transcribió la misma palabra de dos formas ("antes..." / "ante"). Con
        // coincidencia exacta, la duplicación entera se colaba.
        var resultado = Solapamiento.Fusionar(
            "Y me presento antes...",
            "y me presento ante todos ustedes en esta materia.");
        Assert.Equal("todos ustedes en esta materia.", resultado);
    }

    [Fact]
    public void NoToleraDiscrepanciaEnSolapesCortos()
    {
        // Con menos de tres palabras, tolerar un fallo borraría texto legítimo:
        // "de" y "la" no son un solape, son coincidencia.
        var resultado = Solapamiento.Fusionar("hablamos de", "la reunión de mañana");
        Assert.Equal("la reunión de mañana", resultado);
    }

    [Fact]
    public void NoBorraTextoCuandoHayDosDiscrepancias()
    {
        var resultado = Solapamiento.Fusionar(
            "el sistema de subtítulos",
            "un método para transcribir");
        Assert.Equal("un método para transcribir", resultado);
    }

    [Theory]
    [InlineData("Mitocondria", "mitocondria")]
    [InlineData("FOTOSÍNTESIS", "fotosintesis")]
    [InlineData("año", "año")]      // la eñe se conserva: distingue palabras
    [InlineData("¿qué?", "que")]
    public void Normalizar_QuitaTildesYSignosPeroConservaEnie(string entrada, string esperado)
    {
        Assert.Equal(esperado, Glosario.Normalizar(entrada));
    }
}
