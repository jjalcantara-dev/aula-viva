using Accesibilidad.Core;

namespace Accesibilidad.Core.Tests;

/// <summary>
/// Casos observados en uso real del sistema, con micrófono abierto y el docente en pausa.
/// Es el fallo más peligroso para accesibilidad: la salida se lee con naturalidad y el
/// alumno no tiene forma de saber que no corresponde a lo dicho.
/// </summary>
public class HallucinationFilterTests
{
    [Theory]
    [InlineData("¡Suscríbete al canal!")]
    [InlineData("suscribete al canal")]                    // sin signos ni tildes
    [InlineData("Bueno, y eso. ¡Suscríbete al canal!")]    // envuelta en texto
    [InlineData("Gracias por ver el vídeo")]
    [InlineData("Subtítulos realizados por la comunidad de Amara.org")]
    public void DetectaMuletillasDelEntrenamiento(string texto)
    {
        Assert.True(HallucinationFilter.EsSospechoso(texto));
    }

    [Theory]
    [InlineData("y y y y y y y y y y y y y y")]
    [InlineData("gracias gracias gracias gracias gracias gracias")]
    public void DetectaBuclesDeRepeticion(string texto)
    {
        Assert.True(HallucinationFilter.EsSospechoso(texto));
    }

    [Theory]
    [InlineData("Mi nombre es Jesús y soy profesor de informática")]
    [InlineData("para el módulo de programación")]
    [InlineData("voy a explicar primero las reglas de clase")]
    // Habla legítima con repetición: el énfasis y el titubeo son parte del habla real y
    // no deben descartarse. Es el falso positivo que hay que evitar.
    [InlineData("no, no, no, eso no es así")]
    [InlineData("es que, es que, es que no me da tiempo a explicarlo todo hoy en clase")]
    public void NoDescartaHablaLegitima(string texto)
    {
        Assert.Null(HallucinationFilter.Motivo(texto));
    }

    [Fact]
    public void DescartaTextoVacio()
    {
        Assert.True(HallucinationFilter.EsSospechoso("   "));
    }

    [Fact]
    public void ElMotivoExplicaElDescarte()
    {
        // El motivo se muestra en la interfaz: el docente debe poder entender por qué el
        // sistema se calló, en lugar de creer que dejó de funcionar.
        var motivo = HallucinationFilter.Motivo("¡Suscríbete al canal!");
        Assert.NotNull(motivo);
        Assert.Contains("muletilla", motivo);
    }

    [Fact]
    public void UnaPalabraRepetidaDentroDeUnaFraseLargaNoEsBucle()
    {
        // Cinco repeticiones, pero no dominan el texto: es énfasis.
        var texto = "la clase de hoy va de programación y la programación es programación "
                    + "aplicada porque programación sin práctica no sirve de nada en absoluto "
                    + "cuando uno aprende programación desde cero";
        Assert.Null(HallucinationFilter.Motivo(texto));
    }
}
