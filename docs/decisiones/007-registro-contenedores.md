# 007 · Registro de contenedores: GHCR y no Docker Hub

**Decisión:** la imagen de la aplicación se publica en GitHub Container Registry (`ghcr.io`).
**Estado:** aplicada · **Fecha:** 9 de septiembre de 2026

## Contexto

`docker-compose.yml` referencia una imagen publicada de la aplicación (`app`), separada de
los servicios de reconocimiento: pesa unos 230 MB frente a las decenas de gigabytes de una
base ROCm o CUDA, y es la que un centro quiere levantar sin instalar el kit de desarrollo de
.NET. Publicarla exige elegir un registro de contenedores.

## Opciones

| | GHCR | Docker Hub |
|---|---|---|
| Autenticación en CI | `secrets.GITHUB_TOKEN`, ya existe, sin cuenta nueva | Cuenta y token de acceso aparte que crear y mantener |
| Límite de descargas anónimas | Sin límite práctico para este uso | Límite de *pulls* por IP; un centro educativo tirando desde la misma IP puede toparse con él |
| Ubicación respecto al código | Mismo repositorio y organización (`github.com/jjalcantara-dev/tfm-ia`) | Servicio tercero más que documentar y enlazar |
| Coherencia con la licencia | El paquete queda público junto al repositorio público que defiende la apertura del código (`006-licencia.md`) | Sin relación directa |

## Decisión

**GHCR.** El flujo de publicación (`.github/workflows/publicar-imagen.yml`) construye y
sube la imagen a `ghcr.io/jjalcantara-dev/tfm-ia/app` al empujar un tag `v*`, autenticado
con el token que la propia Action ya recibe. No hay credencial nueva que gestionar ni
servicio adicional que enlazar desde la documentación de despliegue.

## Consecuencias

- `docker-compose.yml` fija `image: ghcr.io/jjalcantara-dev/tfm-ia/app:${VERSION_APP:-latest}`.
- La imagen solo se publica con un tag de versión (`git tag v0.1.0-beta && git push origin
  v0.1.0-beta`), nunca en cada empuje a `master`: evita que `latest` sea un blanco móvil,
  igual que ya se evita en los resultados de `research/`.
- Si en algún momento el objetivo pasara a ser la máxima distribución posible fuera del
  ecosistema GitHub, la elección correcta sería revisar esta decisión, no acumular un
  segundo registro en paralelo.
