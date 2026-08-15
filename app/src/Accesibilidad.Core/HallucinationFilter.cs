using System.Text.RegularExpressions;

namespace Accesibilidad.Core;

/// <summary>
/// Descarta salidas que el modelo inventa en lugar de reconocer.
///
/// <para><b>Por qué existe.</b> Whisper se entrenó con enormes cantidades de subtítulos de
/// vídeo, así que cuando recibe silencio o audio ininteligible tiende a emitir las frases
/// más frecuentes de ese material en lugar de callarse. En una prueba real del sistema,
/// con el micrófono abierto y el docente en pausa, produjo <i>«¡Suscríbete al canal!»</i>
/// y un bucle de <i>«y y y y y y»</i>.</para>
///
/// <para>Para un sistema de accesibilidad es el fallo más grave posible: la salida es
/// gramatical, se lee con naturalidad y el alumno no tiene ninguna forma de detectar que
/// no corresponde a lo dicho. Un subtítulo ausente se nota; uno inventado, no.</para>
///
/// <para><b>Qué no es.</b> No detecta alucinaciones plausibles en el dominio, y esa
/// limitación está confirmada en uso real: tras incorporar el filtro, el sistema
/// transcribió <i>«me he mantenido en silencio durante la noche»</i> donde el docente
/// había dicho <i>«durante 30 o 40 segundos»</i>. La salida es gramatical, encaja en el
/// contexto y tiene longitud normal; ninguna heurística de superficie la distingue de
/// habla real. Detectarla exigiría contrastar con el audio.</para>
///
/// <para>Cubre por tanto los dos patrones que sí son reconocibles por su forma: las
/// muletillas del corpus de entrenamiento y los bucles de repetición. Es una reducción
/// del riesgo, no una garantía, y así debe presentarse a quien despliegue el sistema.</para>
/// </summary>
public static class HallucinationFilter
{
    /// <summary>
    /// Frases que el modelo emite sobre silencio. Proceden de subtítulos de vídeo, que
    /// abundan en su entrenamiento. La lista es abierta: conviene ampliarla con lo que se
    /// observe en uso real.
    /// </summary>
    /// Las entradas van YA NORMALIZADAS (minúsculas, sin tildes ni signos), porque es
    /// contra esa forma contra la que se comparan: <c>Normalize</c> elimina los signos
    /// dentro de cada palabra, de modo que «Amara.org» queda como «amaraorg».
    private static readonly string[] FrasesInventadas =
    [
        "suscribete al canal",
        "no olvides suscribirte",
        "gracias por ver el video",
        "gracias por ver el vídeo",
        "gracias por su atencion",
        "subtitulos realizados por la comunidad de amaraorg",
        "subtitulado por la comunidad de amaraorg",
        "mas informacion en www",
        "amaraorg",
        "hasta la proxima",
        "nos vemos en el proximo video",
    ];

    /// <summary>
    /// Repeticiones mínimas de la misma palabra para considerarlo un bucle degenerado.
    /// Tres es demasiado poco: «no, no, no» es habla legítima y frecuente.
    /// </summary>
    private const int RepeticionesParaBucle = 5;

    private static readonly Regex Espacios = new(@"\s+", RegexOptions.Compiled);

    /// <summary>Motivo del descarte, o <c>null</c> si el texto parece legítimo.</summary>
    public static string? Motivo(string texto)
    {
        if (string.IsNullOrWhiteSpace(texto)) return "vacío";

        var normalizado = Espacios.Replace(
            string.Join(' ', texto.Split(' ').Select(Glossary.Normalize)), " ").Trim();

        if (normalizado.Length == 0) return "sin contenido";

        foreach (var frase in FrasesInventadas)
        {
            // Contención y no igualdad: el modelo suele envolverlas en signos o unirlas
            // a algún fragmento real.
            if (normalizado.Contains(frase, StringComparison.Ordinal))
                return $"muletilla del entrenamiento: «{frase}»";
        }

        var palabras = normalizado.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (EsBucle(palabras, out var repetida))
            return $"bucle de repetición: «{repetida}»";

        return null;
    }

    public static bool EsSospechoso(string texto) => Motivo(texto) is not null;

    /// <summary>
    /// Detecta que una misma palabra ocupa casi todo el segmento. Se exige además que
    /// domine el texto: repetir una palabra cinco veces dentro de una frase larga es
    /// énfasis, no degeneración.
    /// </summary>
    private static bool EsBucle(string[] palabras, out string repetida)
    {
        repetida = "";
        if (palabras.Length < RepeticionesParaBucle) return false;

        var grupos = palabras.GroupBy(p => p)
                             .Select(g => (Palabra: g.Key, Veces: g.Count()))
                             .OrderByDescending(g => g.Veces)
                             .First();

        if (grupos.Veces >= RepeticionesParaBucle &&
            grupos.Veces >= palabras.Length * 0.6)
        {
            repetida = grupos.Palabra;
            return true;
        }
        return false;
    }
}
