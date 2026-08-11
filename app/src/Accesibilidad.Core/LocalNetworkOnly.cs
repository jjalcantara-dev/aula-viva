using System.Net;
using System.Net.Sockets;

namespace Accesibilidad.Core;

/// <summary>
/// Comprueba si una dirección pertenece a una red privada.
///
/// <para><b>Por qué el sistema se limita a la red local.</b> La aplicación difunde audio
/// de aula transcrito: voces identificables, a menudo de menores. Exponerla a internet
/// sería un problema de protección de datos antes que técnico, y no se resolvería con
/// añadir una contraseña.</para>
///
/// <para>No basta con "no abrir el puerto en el router": un reenvío hecho por error o un
/// equipo con IP pública dejarían el sistema accesible sin que nadie se entere. Que sea la
/// propia aplicación la que rechace lo que no venga de una red privada convierte la
/// restricción en algo verificable, no en una suposición sobre la configuración de red.</para>
///
/// <para>Si algún día hiciera falta acceso remoto, la vía correcta es una VPN al centro:
/// el dispositivo entra en la red local y esta comprobación lo acepta sin cambiar nada.</para>
/// </summary>
public static class LocalNetworkOnly
{
    /// <summary>Rangos privados de IPv4 según RFC 1918, más bucle local y enlace local.</summary>
    public static bool IsPrivate(IPAddress? address)
    {
        if (address is null) return false;

        if (address.IsIPv4MappedToIPv6) address = address.MapToIPv4();

        if (address.AddressFamily == AddressFamily.InterNetworkV6)
        {
            // ::1 (bucle), fc00::/7 (únicas locales), fe80::/10 (enlace local).
            return IPAddress.IsLoopback(address)
                   || address.IsIPv6LinkLocal
                   || (address.GetAddressBytes()[0] & 0xFE) == 0xFC;
        }

        if (IPAddress.IsLoopback(address)) return true;

        var b = address.GetAddressBytes();
        return b[0] switch
        {
            10 => true,                                  // 10.0.0.0/8
            172 => b[1] >= 16 && b[1] <= 31,             // 172.16.0.0/12
            192 => b[1] == 168,                          // 192.168.0.0/16
            169 => b[1] == 254,                          // 169.254.0.0/16 (enlace local)
            _ => false,
        };
    }
}
