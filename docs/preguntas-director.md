# Preguntas abiertas para el director

Cola viva. Marcar como ✅ cuando se resuelva y anotar el acuerdo en `docs/reuniones/`.

> ⚠️ **Sin director asignado a fecha de M0** (ver R15 en `PLANNING.md`). Mientras tanto:
> no quedarse parado. Para cada punto bloqueante, tomar una **decisión provisional
> razonable**, dejar constancia del porqué en `docs/decisiones/` y marcarla como revisable.
> Todas las cifras de este documento están medidas, no supuestas: la primera reunión
> debería poder cerrarse en una sesión.

## Bloqueantes — cerrar en F0

- [ ] **Corpus.** ¿Se acepta corpus público no educativo documentando el desajuste de
      dominio? ¿Material educativo con subtítulos verificados a mano? ¿Grabación propia?
      *Es el riesgo nº 1 del proyecto (R1).*
- [ ] **Técnicas comprometidas.** ¿Las tres o dos + una opcional?
      *Nota: el entorno GPU está validado para entrenar, así que LoRA ya no es
      técnicamente inviable. La restricción que queda es de datos y de tiempo.*
- [ ] **Métricas.** ¿Basta WER/CER agregados, o se exige una métrica orientada a
      accesibilidad (acierto sobre terminología del dominio)?
      *Ver hallazgo de normalización más abajo: la elección de métrica no es neutral.*
- [ ] **Evaluación de la app.** ¿Demo funcional, o validación formal con usuarios /
      evaluación heurística de accesibilidad? *Impacto de ~6 semanas.*

## Metodológicas — cerrar antes de H2 (protocolo congelado)

- [ ] **Normalización de texto.** En la primera medición el WER pasa de **20.7% a 6.2%**
      solo por normalizar mayúsculas y puntuación. Hay que fijar y justificar en la
      memoria qué se perdona. ¿Se acepta la normalización básica como métrica principal?
- [ ] **Números y acrónimos.** Medido en M0 sobre `whisper-medium`: **el 43% de las
      sustituciones son numerales** (`'ocho' → '8'`, `'quince' → '15'`) o expansión
      correcta de abreviaturas (`'ee','uu' → 'estados','unidos'`). No son errores
      acústicos. Descontarlos baja el WER de 3.01% a ~1.7%. ¿Se normalizan?
- [ ] **Calidad de la referencia (R11).** En la misma muestra el modelo produce
      `'mayorca' → 'mallorca'` y `'velásquez' → 'velázquez'`: **escribe mejor que la
      transcripción de referencia** y se le penaliza. ¿Se acepta auditar y corregir a
      mano una muestra del corpus, y documentarlo como parte del método?
- [ ] **Variedad dialectal (R13).** Todo lo medido en M0 es latinoamericano (FLEURS
      `es_419`, CIEMPIESS mexicano). Si el destino es un centro español, ninguna cifra es
      representativa. ¿Conjunto de evaluación peninsular único, o la variedad entra como
      **factor explícito** de la comparativa? La segunda opción convierte una limitación
      en un resultado.
- [ ] **Significancia estadística.** ¿Se exigen intervalos de confianza o tests, o basta
      reportar variabilidad? *Dato de M0: con 499 palabras el IC95 del WER es de ±1.5
      puntos, y `medium`/`turbo`/`large-v3` resultan indistinguibles. Hacen falta del
      orden de 30.000 palabras (3-4 h) para detectar diferencias de 0.5 puntos.*
- [ ] **Umbral de latencia** que define "tiempo real" en este trabajo. Necesita un número.

## Sobre la memoria

- [ ] **Orden de capítulos.** La plantilla pone Requisitos (3) antes que Objetivos (4), y
      "Identificación de Requisitos" encaja mal en un trabajo de investigación.
      ¿Se admite usarlo para requisitos duales (app + diseño experimental)?
- [ ] **Capítulo 5.** ¿Se admite estructurarlo en secciones separadas (metodología
      experimental / resultados / desarrollo de la aplicación) o desdoblarlo?
- [ ] **Peso relativo Tipo 2 vs Tipo 3** en la evaluación.
- [ ] **Extensión, formato de entrega y anexos exigidos** (la plantilla no lo dice).
- [ ] **Fecha real de la convocatoria** — el planning está en fases relativas hasta saberla.

## Legales / éticas

- [ ] Si se graba audio real de aula: consentimiento informado, anonimización, y si el
      repositorio podrá ser público.
- [ ] ¿Se acepta el uso de cómputo externo si en algún momento hiciera falta?
