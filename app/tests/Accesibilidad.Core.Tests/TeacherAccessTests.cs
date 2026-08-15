using Accesibilidad.Core;

namespace Accesibilidad.Core.Tests;

/// <summary>
/// Separa el puesto de emisión de la vista del alumnado. No es autenticación de usuarios
/// y no pretende serlo; la restricción de fondo la impone <see cref="LocalNetworkOnly"/>.
///
/// <para>Lo que se fija aquí es sobre todo el camino de la clave vacía, porque es el que
/// deja la emisión abierta y el que trae por defecto el fichero de configuración. Que ese
/// comportamiento sea deliberado no lo exime de estar cubierto: si alguien lo invierte
/// por error, el modo de desarrollo pasaría a bloquear el aula o, peor, el modo con clave
/// pasaría a dejarla pasar.</para>
/// </summary>
public class TeacherAccessTests
{
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void SinClaveConfiguradaLaEmisionQuedaAbierta(string? clave)
    {
        var acceso = new TeacherAccess(clave);

        Assert.False(acceso.IsRequired);   // la interfaz usa esto para advertirlo
        Assert.True(acceso.Verify(null));
        Assert.True(acceso.Verify(""));
        Assert.True(acceso.Verify("lo que sea"));
    }

    [Fact]
    public void ConClaveConfiguradaSoloPasaLaCorrecta()
    {
        var acceso = new TeacherAccess("clave-del-aula");

        Assert.True(acceso.IsRequired);
        Assert.True(acceso.Verify("clave-del-aula"));
        Assert.False(acceso.Verify("clave-del-aul"));    // prefijo
        Assert.False(acceso.Verify("clave-del-aulaX"));  // sufijo
        Assert.False(acceso.Verify("Clave-Del-Aula"));   // la caja importa
        Assert.False(acceso.Verify(null));
        Assert.False(acceso.Verify(""));
    }

    [Fact]
    public void AceptaClavesConAcentosYEnie()
    {
        // La clave la escribe un docente en español y viaja como UTF-8 por la
        // configuración. Comparar bytes exige que ambos lados se codifiquen igual.
        var acceso = new TeacherAccess("añoAcadémico2027");

        Assert.True(acceso.Verify("añoAcadémico2027"));
        Assert.False(acceso.Verify("anoAcademico2027"));
    }
}
