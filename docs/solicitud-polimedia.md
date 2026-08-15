# Solicitud de acceso al corpus poliMedia (MLLP-VRAIN, UPV)

**Estado:** listo para enviar, pendiente de rellenar dos campos · **Prioridad:** alta,
desbloquea el dominio educativo real (R1, camino crítico)

> ⚠️ **La memoria afirma que esta solicitud ya se cursó.** Cap. 2 («Se cursó una solicitud
> institucional al grupo responsable, que no obtuvo respuesta»), cap. 6 («quedó cursada sin
> resolución») y el apéndice de riesgos (R1 → «Materializado»). Mientras este correo no
> salga, esas tres frases son falsas y son comprobables por cualquier miembro del tribunal
> con un correo al MLLP. Al enviarlo, marcar la fecha en el registro del final y revisar que
> el README quede coherente.

## Destinatario

**`mllp@upv.es`** — grupo MLLP (Machine Learning and Language Processing), integrado en el
instituto VRAIN de la Universitat Politècnica de València. Universidad **pública**.

> Edifici 1F (DSIC), Camí de Vera s/n, 46022 València · (+34) 96 387 70 00
> Lista de contacto alternativa: `listas.upv.es/mailman/listinfo/mllp-contact`

Dirección obtenida de fuentes públicas; su web (`mllp.upv.es`) rechazó la conexión desde
este equipo durante M0, así que **conviene confirmarla antes de enviar**. Si sigue caída,
la lista de contacto es la vía alternativa.

## Antes de enviar

- [ ] **Rellenar los dos campos entre `[...]`**: el correo de contacto y, si lo hay, el
      teléfono. Ver la nota sobre la dirección institucional más abajo
- [ ] Confirmar que `mllp@upv.es` sigue activa
- [ ] **Sin director asignado todavía.** Una petición avalada por un profesor pesa más. Se
      envía igual indicando que la dirección está pendiente, y **se reenvía añadiendo al
      director** cuando lo haya: el tiempo de respuesta institucional es el recurso escaso,
      no el número de correos
- [ ] Comprobar al responder si hay acuerdo de cesión de datos que firmar
- [ ] Si en dos semanas no hay respuesta, **reenviar una vez** y seguir con el plan B
      (`teleconciencia_es` ampliado + `voxpopuli_es`). No bloquear el proyecto

> **Sobre la dirección de correo.** Enviarlo desde la cuenta de la universidad, si UNIR
> proporciona una, mejora bastante la probabilidad de respuesta: una petición entre
> instituciones se atiende antes que una desde un correo personal, y evita el filtro de
> spam. Si no hay cuenta institucional, adjuntar o mencionar la matrícula.

---

## Borrador

**Asunto:** Solicitud de acceso al corpus poliMedia para Trabajo Fin de Máster (ASR en
dominio educativo)

Estimados miembros del grupo MLLP-VRAIN:

Me pongo en contacto con ustedes en relación con el corpus **poliMedia** de transcripciones
manuales de clases en español, generado en el marco del proyecto europeo transLectures.

Soy estudiante del Máster en Inteligencia Artificial de la Universidad Internacional de La
Rioja (UNIR) y estoy terminando mi Trabajo Fin de Máster sobre **adaptación de modelos de
reconocimiento automático del habla al dominio educativo en español**, con el objetivo
aplicado de generar subtítulos en tiempo real como apoyo a la accesibilidad de alumnado con
discapacidad auditiva en el aula. La dirección del trabajo está pendiente de asignación por
parte de la universidad.

Les escribo con el trabajo experimental ya realizado, porque es precisamente el resultado lo
que motiva la petición. He comparado tres técnicas de adaptación sobre Whisper con diseño
pareado, intervalos por bootstrap y test de signos, y he auditado cinco corpus públicos en
español para elegir el material de evaluación. De esa auditoría salen dos conclusiones que
me llevan hasta ustedes:

- Lo que domina la tasa de error no es la variedad dialectal sino **el registro**: entre
  leer un texto y hablar de forma espontánea el error se multiplica por siete en mi
  medición, mientras que entre español peninsular y mexicano a registro parecido la
  diferencia es de décimas.
- Ninguno de los sustitutos disponibles cubre el registro de clase magistral. Los mejores
  que he encontrado son charlas divulgativas y debate parlamentario, y de los dos corpus de
  habla espontánea que existen en español con transcripción abierta, ambos omiten las tildes
  de forma sistemática, lo que además impide usarlos para ajuste fino sin optimizar hacia el
  error.

El resultado es que mis conclusiones son, en rigor, conclusiones sobre dominios sustitutos y
no sobre el dominio objetivo, y así lo declaro como limitación de fondo del trabajo.
poliMedia es el único recurso que he identificado que reúne las tres condiciones a la vez:
clase universitaria real, lengua española y transcripción verificada por personas.

**Sobre lo que pediría, y sobre el uso previsto, quiero ser completamente transparente:**

- Me sería suficiente un **subconjunto de evaluación de tres o cuatro horas**. No necesito
  las más de ciento quince horas transcritas: mi cálculo de potencia estadística sitúa en
  unas treinta mil palabras de referencia el mínimo para detectar los efectos que estudio, y
  eso son tres o cuatro horas de audio. Un subconjunto pequeño resuelve el problema entero.
- El **corpus no se redistribuiría** en ningún caso: ni audio ni transcripciones, en ningún
  repositorio, ni siquiera parcialmente.
- La **aplicación de subtitulado** sí tengo intención de publicarla como código abierto al
  terminar, para que cualquier centro educativo pueda desplegarla. Sería únicamente el
  código: no incluiría datos de ustedes de ninguna forma.
- La fuente se citaría explícitamente en la memoria y en cualquier material derivado, en los
  términos que ustedes indiquen.

Me gustaría plantearles cuatro preguntas:

1. Si el corpus sigue disponible para uso investigador y bajo qué condiciones.
2. Qué procedimiento debo seguir para solicitar el acceso, y si hay que firmar algún acuerdo
   de cesión de datos.
3. **Si el trabajo incluyera un ajuste fino del modelo sobre su corpus, ¿permitirían
   publicar los pesos resultantes en abierto, o preferirían que ese modelo quedara
   restringido al ámbito académico del trabajo?** Entiendo que un modelo entrenado sobre sus
   datos constituye una obra derivada y que esa decisión les corresponde.
4. Si existe ya un subconjunto reducido pensado para evaluación, en caso de que el corpus
   completo no pueda cederse.

Por último, y con toda modestia dado que el trabajo es de máster: si les resultara de alguna
utilidad, quedo a su disposición para compartir la auditoría de calidad de referencia de los
cinco corpus en español, y las dos métricas complementarias que he tenido que construir
porque la tasa de error de palabra oculta los fallos que importan en accesibilidad, como
perder una negación. Es material que ha salido del trabajo y que quizá tenga interés para un
grupo que ya trabaja sobre transcripción de clases.

Quedo a su disposición para ampliar cualquier detalle o para aportar la acreditación
académica que consideren necesaria.

Agradeciendo de antemano su tiempo, reciban un cordial saludo.

Jesús Jiménez Alcántara
Máster Universitario en Inteligencia Artificial — Universidad Internacional de La Rioja (UNIR)
[correo de contacto] · [teléfono, opcional]

---

## Registro de gestiones

| Fecha | Acción | Resultado |
|---|---|---|
| | Envío inicial | |
| | Reenvío (añadiendo director) | |
| | Respuesta | |

> Rellenar en cuanto se envíe. La fecha de esta tabla es lo que respalda la frase de la
> memoria; hoy no hay nada que la respalde.
