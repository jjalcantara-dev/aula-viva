using Accesibilidad.Core;

namespace Accesibilidad.Core.Tests;

/// <summary>
/// El glosario resuelve RF4 marcando en el subtítulo la terminología que el docente
/// declara importante.
///
/// <para><b>Por qué estas pruebas y no otras.</b> <see cref="Glossary.Normalize"/> es la
/// función de la eñe: el proyecto cometió DOS veces el mismo error, una en Python y otra
/// aquí, comprobando <c>c == 'ñ'</c> después de descomponer en Unicode, donde «ñ» ya es
/// «n» más una tilde combinante y la comprobación no se cumple nunca. En español eso no es
/// cosmético: convierte «año» en «ano». El código está bien; lo que faltaba era algo que
/// impidiera romperlo una tercera vez.</para>
/// </summary>
public class GlossaryTests
{
    [Fact]
    public void LaEnieSobreviveALaNormalizacion()
    {
        // La prueba que cierra el incidente: si alguien vuelve a mover la protección de la
        // eñe a DESPUÉS de descomponer, estas dos palabras colisionan y esto falla.
        Assert.NotEqual(Glossary.Normalize("ano"), Glossary.Normalize("año"));
        Assert.Equal("año", Glossary.Normalize("Año"));
        Assert.Equal("año", Glossary.Normalize("AÑO"));
        Assert.Equal("enseñanza", Glossary.Normalize("Enseñanza,"));
    }

    [Theory]
    [InlineData("Fotosíntesis", "fotosintesis")]   // pierde la tilde
    [InlineData("MITOCONDRIA", "mitocondria")]     // pierde la caja
    [InlineData("«célula».", "celula")]            // pierde los signos
    [InlineData("ADN", "adn")]
    [InlineData("H2O", "h2o")]                     // conserva los dígitos
    public void NormalizaCajaTildesYSignos(string entrada, string esperado) =>
        Assert.Equal(esperado, Glossary.Normalize(entrada));

    [Fact]
    public void MarcaElTerminoAunqueElMotorNoLoAcentueIgual()
    {
        // El motor ASR no acentúa ni puntúa igual que un glosario escrito a mano, así que
        // la coincidencia ignora ambas cosas. Es la razón de ser de Normalize.
        var g = new Glossary(["fotosíntesis"]);
        var conceptos = g.Detect("hablamos de la fotosintesis de las plantas");

        Assert.Single(conceptos);
        Assert.Equal("fotosintesis", conceptos[0]);
    }

    [Fact]
    public void LosFragmentosReconstruyenElTextoExacto()
    {
        // Mark devuelve trozos, no HTML, para que el texto del modelo no se interpole
        // nunca en marcado. La vista lo escapa. Aquí se comprueba lo que eso exige: que
        // la concatenación de los trozos sea el original, carácter a carácter.
        const string texto = "La mitocondria, ¿recuerdas?, produce ATP.";
        var g = new Glossary(["mitocondria", "ATP"]);

        var trozos = g.Mark(texto);

        Assert.Equal(texto, string.Concat(trozos.Select(t => t.Text)));
        Assert.Equal(2, trozos.Count(t => t.IsConcept));
    }

    [Fact]
    public void SinTerminosDevuelveElTextoEnUnSoloFragmentoSinMarcar()
    {
        var trozos = new Glossary([]).Mark("cualquier cosa");

        Assert.Single(trozos);
        Assert.False(trozos[0].IsConcept);
        Assert.Equal("cualquier cosa", trozos[0].Text);
    }

    [Fact]
    public void LosTerminosCompuestosSeConservanPeroNoSeMarcan()
    {
        // Buscarlos exige n-gramas y está declarado fuera de alcance. Lo que NO puede
        // pasar es que desaparezcan de la lista que ve el docente en la interfaz.
        var g = new Glossary(["energía de activación", "catalizador"]);

        Assert.Contains("energía de activación", g.Terms);
        Assert.Empty(g.Detect("la energía de activación baja"));
        Assert.Single(g.Detect("el catalizador la baja"));
    }

    [Fact]
    public void DescartaEntradasVaciasYRepetidas()
    {
        var g = new Glossary(["  celula ", "celula", "", "   ", "ADN"]);

        Assert.Equal(2, g.Terms.Count);
        Assert.Contains("celula", g.Terms);
        Assert.Contains("ADN", g.Terms);
    }

    [Fact]
    public void NoMarcaCoincidenciasParcialesDentroDeOtraPalabra()
    {
        // «célula» no debe encenderse dentro de «celulares»: la comparación es por
        // palabra completa, no por subcadena.
        var g = new Glossary(["célula"]);

        Assert.Empty(g.Detect("los datos celulares del alumnado"));
        Assert.Single(g.Detect("la célula eucariota"));
    }
}
