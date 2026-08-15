using Accesibilidad.Asr;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Accesibilidad.Core.Tests;

/// <summary>
/// El fichero de configuración lleva claves <c>_comentario</c> para explicar cada sección
/// a quien despliegue el sistema. En casi todas son inertes, porque se enlazan a objetos
/// que ignoran las claves que no conocen.
///
/// <para><b>En <c>Logging:LogLevel</c> no lo son.</b> Esa sección no se enlaza a un objeto:
/// se recorre entera tratando cada par como «categoría de registro» → «nivel», así que un
/// comentario ahí se intenta convertir a <see cref="LogLevel"/> y tumba el arranque del
/// host con <c>InvalidOperationException</c>. Ocurrió: la aplicación entró en bucle de
/// reinicio dentro del contenedor y el error no apuntaba al fichero de configuración sino
/// a la construcción del host, que es lo que lo hizo costoso de diagnosticar.</para>
///
/// <para>La prueba monta el mismo canal que monta la aplicación en lugar de limitarse a
/// validar el JSON: el fichero era JSON perfectamente válido cuando falló.</para>
/// </summary>
public class ConfiguracionTests
{
    private static string RutaAppSettings()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "TFM-IA.sln"))
                               && !Directory.Exists(Path.Combine(dir.FullName, ".git")))
            dir = dir.Parent;

        Assert.NotNull(dir);
        var ruta = Path.Combine(dir!.FullName, "app", "src", "Accesibilidad.Web", "appsettings.json");
        Assert.True(File.Exists(ruta), $"no se encuentra {ruta}");
        return ruta;
    }

    [Fact]
    public void LaConfiguracionDeRegistroSeEnlazaSinRomperElArranque()
    {
        var configuracion = new ConfigurationBuilder()
            .AddJsonFile(RutaAppSettings(), optional: false)
            .Build();

        var servicios = new ServiceCollection();
        servicios.AddLogging(b => b.AddConfiguration(configuracion.GetSection("Logging")));

        using var proveedor = servicios.BuildServiceProvider();

        // Resolver la fábrica es lo que dispara la lectura de las reglas. Si alguien vuelve
        // a meter un comentario bajo LogLevel, revienta aquí y no en producción.
        var excepcion = Record.Exception(() => proveedor.GetRequiredService<ILoggerFactory>());
        Assert.Null(excepcion);
    }

    [Fact]
    public void TodoValorBajoLogLevelEsUnNivelDeRegistro()
    {
        // Comprobación directa además de la anterior, porque su mensaje de fallo dice qué
        // clave sobra; el de la otra solo dice que el host no arranca.
        var configuracion = new ConfigurationBuilder()
            .AddJsonFile(RutaAppSettings(), optional: false)
            .Build();

        foreach (var entrada in configuracion.GetSection("Logging:LogLevel").GetChildren())
        {
            Assert.True(Enum.TryParse<LogLevel>(entrada.Value, ignoreCase: true, out _),
                $"«{entrada.Key}» vale «{entrada.Value}», que no es un LogLevel. "
                + "Los comentarios no pueden vivir dentro de Logging:LogLevel.");
        }
    }

    /// <summary>
    /// El enlace de configuración de .NET es por NOMBRE DE PROPIEDAD y falla en silencio:
    /// una sección que no coincide se ignora y el objeto se queda con sus valores por
    /// defecto, sin excepción ni aviso. Ocurrió con dos secciones a la vez, por un
    /// renombrado de identificadores a inglés que no llegó al fichero de configuración:
    /// <c>Asr:Segmentacion</c> frente a <c>Segmentation</c>, y <c>Glosario:Terminos</c>
    /// frente a <c>Glossary:Terms</c>. La segunda dejaba el glosario vacío en todos los
    /// despliegues, de modo que RF4 no marcaba nada y ningún error lo delataba.
    ///
    /// <para>La prueba enlaza como enlaza <c>Program.cs</c>, no como debería.</para>
    /// </summary>
    [Fact]
    public void LaSeccionDeSegmentacionLlegaAlObjetoDeOpciones()
    {
        var configuracion = new ConfigurationBuilder()
            .AddJsonFile(RutaAppSettings(), optional: false)
            .Build();

        var opciones = configuracion.GetSection("Asr").Get<WhisperOptions>();
        Assert.NotNull(opciones);

        var enFichero = configuracion.GetSection("Asr:Segmentation");
        Assert.True(enFichero.Exists(),
            "no existe la sección Asr:Segmentation. Si se renombró en el JSON, el enlace "
            + "se rompe sin dar error y se usan los valores por defecto de C#.");

        // Los valores del fichero deben ser los que acaba usando el segmentador; que
        // coincidan con los de C# por casualidad es justo lo que enmascaró el fallo.
        Assert.Equal(enFichero.GetValue<double>("MaxSeconds"), opciones!.Segmentation.MaxSeconds);
        Assert.Equal(enFichero.GetValue<double>("MinSeconds"), opciones.Segmentation.MinSeconds);
        Assert.Equal(enFichero.GetValue<double>("MinSilenceSeconds"),
            opciones.Segmentation.MinSilenceSeconds);
        Assert.Equal(enFichero.GetValue<double>("SilenceFactor"),
            opciones.Segmentation.SilenceFactor);
    }

    /// <summary>
    /// Los valores por defecto que describe la memoria (sección «Los componentes del
    /// núcleo») son los que la aplicación carga de verdad. Si alguien ajusta uno sin
    /// tocar el texto, o al revés, esto lo dice.
    /// </summary>
    [Fact]
    public void LosValoresPorDefectoSonLosDocumentadosEnLaMemoria()
    {
        var configuracion = new ConfigurationBuilder()
            .AddJsonFile(RutaAppSettings(), optional: false)
            .Build();

        var s = configuracion.GetSection("Asr").Get<WhisperOptions>()!.Segmentation;

        // Tope: fila ganadora de exp-102 (WER 12.48%, media 2.93 s, p95 5.92 s).
        Assert.Equal(8.0, s.MaxSeconds);
        Assert.Equal(1.5, s.MinSeconds);
        Assert.Equal(0.3, s.MinSilenceSeconds);
        Assert.Equal(0.35, s.SilenceFactor);

        // Y que el objeto sin configurar coincida con el fichero: si divergen, la memoria
        // describe uno de los dos y no se sabe cuál.
        var porDefecto = new SegmentationOptions();
        Assert.Equal(porDefecto.MaxSeconds, s.MaxSeconds);
        Assert.Equal(porDefecto.MinSeconds, s.MinSeconds);
        Assert.Equal(porDefecto.MinSilenceSeconds, s.MinSilenceSeconds);
        Assert.Equal(porDefecto.SilenceFactor, s.SilenceFactor);
    }

    /// <summary>
    /// El glosario configurado tiene que llegar al objeto. Estuvo vacío en todos los
    /// despliegues porque <c>Program.cs</c> leía <c>Glossary:Terms</c> y el fichero traía
    /// <c>Glosario:Terminos</c>; el <c>?? []</c> se tragaba el fallo.
    /// </summary>
    [Fact]
    public void ElGlosarioConfiguradoLlegaAlObjeto()
    {
        var configuracion = new ConfigurationBuilder()
            .AddJsonFile(RutaAppSettings(), optional: false)
            .Build();

        var terminos = configuracion.GetSection("Glossary:Terms").Get<string[]>() ?? [];
        Assert.NotEmpty(terminos);

        var glosario = new Glossary(terminos);
        Assert.NotEmpty(glosario.Terms);
        // Y que sirvan para algo: al menos uno debe poder marcarse en un subtítulo.
        var alguno = glosario.Terms.First(t => !t.Contains(' '));
        Assert.Single(glosario.Detect($"esto trata de {alguno} y poco más"));
    }
}
