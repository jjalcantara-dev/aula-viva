namespace Accesibilidad.Core;

/// <summary>
/// Une segmentos consecutivos eliminando el texto que se repite por el solapamiento
/// de ventanas.
///
/// <para><b>Por qué es imprescindible y no una mejora opcional.</b> El barrido exp-100
/// midió el coste de no hacerlo: con ventanas de 1-2 segundos y solapamiento, el WER
/// supera el <b>100%</b> — el sistema emite más palabras erróneas que palabras tiene la
/// referencia, porque cada fragmento repite el final del anterior. Sin deduplicación,
/// el subtitulado en vivo es inservible por debajo de ventanas de 8 segundos.</para>
///
/// <para>El método es el estándar: buscar el mayor solape entre el final del texto
/// acumulado y el principio del nuevo, y recortarlo.</para>
/// </summary>
public static class OverlapMerger
{
    /// <summary>
    /// Máximo de palabras que se buscan como solape. Limita el coste y evita falsos
    /// positivos: una coincidencia larguísima es más probable que sea repetición real
    /// del hablante que duplicación de ventana.
    /// </summary>
    private const int MaximoPalabras = 30;

    /// <summary>
    /// Mínimo de palabras para aceptar un solape con una discrepancia. Con solapes muy
    /// cortos, tolerar fallos produciría falsos positivos y borraría texto legítimo.
    /// </summary>
    private const int MinimoParaTolerancia = 3;

    /// <summary>Palabras nuevas de <paramref name="nuevo"/> tras descartar el solape.</summary>
    public static string Merge(string anterior, string nuevo)
    {
        if (string.IsNullOrWhiteSpace(anterior)) return nuevo.Trim();
        if (string.IsNullOrWhiteSpace(nuevo)) return string.Empty;

        var cola = Palabras(anterior);
        var cabeza = Palabras(nuevo);
        var maximo = Math.Min(MaximoPalabras, Math.Min(cola.Length, cabeza.Length));

        // Primero se busca coincidencia exacta, de mayor a menor: interesa el solape más
        // largo, no el primero que aparezca.
        for (var k = maximo; k > 0; k--)
        {
            if (Discrepancias(cola, cabeza, k) == 0)
                return string.Join(' ', cabeza[k..]);
        }

        // Segunda pasada, tolerante. En la frontera entre ventanas el modelo tiene el
        // audio cortado y suele transcribir esa palabra de forma distinta en cada una:
        // medido en uso real, "y me presento antes..." frente a "y me presento ante
        // todos ustedes". Exigir coincidencia exacta deja pasar la duplicación entera
        // por una sola palabra.
        for (var k = maximo; k >= MinimoParaTolerancia; k--)
        {
            if (Discrepancias(cola, cabeza, k) <= 1)
                return string.Join(' ', cabeza[k..]);
        }

        return nuevo.Trim();
    }

    /// <summary>Palabras que no coinciden entre el final de <paramref name="cola"/> y el
    /// principio de <paramref name="cabeza"/>, comparando <paramref name="k"/> posiciones.
    /// Se detiene en cuanto supera dos, que ya descarta el solape.</summary>
    private static int Discrepancias(string[] cola, string[] cabeza, int k)
    {
        var fallos = 0;
        for (var i = 0; i < k; i++)
        {
            // Se comparan formas normalizadas: el modelo puntúa y capitaliza distinto
            // en cada ventana, y comparar en crudo no detectaría el solape.
            if (Glossary.Normalize(cola[^(k - i)]) != Glossary.Normalize(cabeza[i]))
            {
                if (++fallos > 1) return fallos;
            }
        }
        return fallos;
    }

    private static string[] Palabras(string texto) =>
        texto.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
}
