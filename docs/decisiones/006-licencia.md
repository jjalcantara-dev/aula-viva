# 006 · Licencia: AGPL-3.0 para la aplicación

**Decisión:** el repositorio se publica bajo **GNU AGPL-3.0**.
**Estado:** aplicada · **Fecha:** 15 de agosto de 2026

## El requisito, y por qué no se puede cumplir literalmente

El requisito planteado fue: *que sea libre, pero que nadie se pueda lucrar con ello*.

Las dos mitades no son compatibles. La definición de código abierto prohíbe expresamente
discriminar por finalidad de uso, y el uso comercial es una finalidad de uso; una licencia
que lo prohíba (las llamadas *non-commercial*) **no es código abierto**, aunque el código
esté a la vista. Elegir una de esas habría obligado a no llamarlo así, incluida la promesa
de publicación que se hace en la solicitud a la UPV.

Conviene además deshacer una suposición: **la licencia más habitual en el ámbito
universitario no es la no comercial, sino la permisiva** (MIT, BSD, Apache-2.0). Las
condiciones no comerciales son frecuentes en los *conjuntos de datos*, no en el código; el
propio Europarl-ST del grupo MLLP se distribuye como CC BY-NC 4.0, y eso restringe los
datos, no un programa.

## Qué se hace en su lugar

AGPL-3.0 no prohíbe cobrar, que es lo que no se puede prohibir sin dejar de ser libre, pero
**elimina el incentivo de apropiárselo**, que es lo que de verdad preocupaba:

- Cualquiera puede desplegarlo, modificarlo y cobrar por instalarlo o mantenerlo. Un centro
  puede pagar a una empresa para que se lo despliegue, que es un escenario deseable.
- Quien lo modifique y lo ofrezca **como servicio en red** está obligado a publicar sus
  cambios. Ese es el punto: cierra el hueco que la GPL corriente deja abierto, y es
  exactamente la forma que tendría un tercero de convertir esto en un producto cerrado,
  porque el sistema se usa por red desde el navegador.
- Las mejoras vuelven a la comunidad educativa, que es el destinatario del trabajo.

## Compatibilidad, comprobada

Ninguna dependencia lo impide. Whisper es MIT, PyTorch es BSD, Transformers y la biblioteca
de adaptadores son Apache-2.0, y la pila de .NET es MIT: todas permisivas, y por tanto
incorporables en un proyecto con copyleft. La dirección contraria no funcionaría, pero no
es la que se necesita.

**El corpus queda fuera de esta licencia y debe seguir así.** La licencia cubre el código;
el audio y las transcripciones no se redistribuyen en ningún caso, y su procedencia impone
sus propias condiciones (RL4).

## El coste, declarado

AGPL tiene una contrapartida real y conviene no ocultarla: hay organizaciones con políticas
internas que rechazan el copyleft de red, de modo que un integrador que quisiera incluir
esto en un producto propietario no podrá. Es una consecuencia buscada, no un efecto
secundario; pero si el objetivo pasara a ser la máxima adopción posible por encima de todo,
la elección correcta sería Apache-2.0 y este documento habría que rehacerlo.
