using System.Net;
using Accesibilidad.Core;

namespace Accesibilidad.Core.Tests;

/// <summary>
/// Es la barrera que impide que el audio de un aula acabe siendo accesible desde internet.
/// Un fallo aquí no da error ni se nota: el sistema sigue funcionando, solo que abierto.
/// </summary>
public class LocalNetworkOnlyTests
{
    [Theory]
    [InlineData("127.0.0.1")]        // bucle local
    [InlineData("10.0.0.5")]         // 10.0.0.0/8
    [InlineData("172.16.4.1")]       // 172.16.0.0/12, límite inferior
    [InlineData("172.31.255.254")]   // 172.16.0.0/12, límite superior
    [InlineData("192.168.1.50")]     // típica de router doméstico
    [InlineData("169.254.10.1")]     // enlace local (sin DHCP)
    [InlineData("::1")]              // bucle IPv6
    [InlineData("fd00::1")]          // única local IPv6
    public void AceptaDireccionesDeRedLocal(string ip)
    {
        Assert.True(LocalNetworkOnly.IsPrivate(IPAddress.Parse(ip)));
    }

    [Theory]
    [InlineData("8.8.8.8")]
    [InlineData("172.15.0.1")]       // justo FUERA del rango 172.16-31
    [InlineData("172.32.0.1")]       // justo FUERA por arriba
    [InlineData("192.167.1.1")]      // parecida a 192.168 pero pública
    [InlineData("2001:4860:4860::8888")]
    public void RechazaDireccionesPublicas(string ip)
    {
        Assert.False(LocalNetworkOnly.IsPrivate(IPAddress.Parse(ip)));
    }

    [Fact]
    public void RechazaDireccionAusente()
    {
        // Sin dirección remota no se puede afirmar que sea local: se deniega.
        Assert.False(LocalNetworkOnly.IsPrivate(null));
    }

    [Fact]
    public void ReconoceIPv4EnvueltaEnIPv6()
    {
        // Kestrel entrega ::ffff:192.168.1.10 cuando escucha en doble pila; sin
        // desenvolverla, una dirección local se tomaría por pública.
        Assert.True(LocalNetworkOnly.IsPrivate(IPAddress.Parse("::ffff:192.168.1.10")));
        Assert.False(LocalNetworkOnly.IsPrivate(IPAddress.Parse("::ffff:8.8.8.8")));
    }

    [Fact]
    public void SinClaveConfiguradaElAccesoQuedaAbierto()
    {
        var acceso = new TeacherAccess(null);
        Assert.False(acceso.IsRequired);
        Assert.True(acceso.Verify(null));
    }

    [Theory]
    [InlineData("correcta", "correcta", true)]
    [InlineData("correcta", "incorrecta", false)]
    [InlineData("correcta", "correct", false)]    // prefijo: no debe colar
    [InlineData("correcta", "", false)]
    [InlineData("correcta", null, false)]
    public void ConClaveSoloAceptaLaExacta(string clave, string? intento, bool esperado)
    {
        Assert.Equal(esperado, new TeacherAccess(clave).Verify(intento));
    }
}
