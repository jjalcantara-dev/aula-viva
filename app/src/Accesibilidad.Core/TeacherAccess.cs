using System.Security.Cryptography;
using System.Text;

namespace Accesibilidad.Core;

/// <summary>
/// Control de acceso al puesto del docente.
///
/// <para><b>Por qué hace falta.</b> La vista del alumno es deliberadamente abierta:
/// cualquiera en el aula debe poder conectarse sin fricción. Pero la de emisión activa el
/// micrófono del equipo y difunde a toda la clase; sin control, cualquier alumno conectado
/// a la red podría tomarla y emitir.</para>
///
/// <para><b>Qué NO es.</b> No es autenticación de usuarios ni sustituye a HTTPS. Es una
/// clave compartida, proporcionada al escenario: red local del centro, un único puesto
/// docente, sin gestión de identidades. La restricción de fondo la impone
/// <see cref="LocalNetworkOnly"/>; esto solo separa el puesto del docente del resto del
/// aula.</para>
/// </summary>
public sealed class TeacherAccess(string? key)
{
    private readonly byte[]? _key = string.IsNullOrWhiteSpace(key)
        ? null : Encoding.UTF8.GetBytes(key);

    /// <summary>
    /// Sin clave configurada la emisión queda abierta. Es el modo de desarrollo, y la
    /// interfaz lo advierte para que no se despliegue así por descuido.
    /// </summary>
    public bool IsRequired => _key is not null;

    public bool Verify(string? attempt)
    {
        if (_key is null) return true;
        if (string.IsNullOrEmpty(attempt)) return false;

        // Comparación de tiempo constante: con una comparación normal, el tiempo de
        // respuesta revela cuántos caracteres iniciales son correctos y la clave se
        // puede adivinar carácter a carácter.
        return CryptographicOperations.FixedTimeEquals(
            Encoding.UTF8.GetBytes(attempt), _key);
    }
}
