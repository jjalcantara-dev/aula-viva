# Aplicacion web de subtitulado. No necesita GPU: todo el reconocimiento ocurre en el
# servicio ASR, con el que se comunica por HTTP.

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

# Solo los proyectos primero: asi la restauracion de paquetes se cachea y un cambio en el
# codigo no obliga a volver a descargarlos.
COPY app/*.slnx ./
COPY app/src/Accesibilidad.Core/*.csproj ./src/Accesibilidad.Core/
COPY app/src/Accesibilidad.Asr/*.csproj  ./src/Accesibilidad.Asr/
COPY app/src/Accesibilidad.Web/*.csproj  ./src/Accesibilidad.Web/
RUN dotnet restore src/Accesibilidad.Web

COPY app/src/ ./src/
RUN dotnet publish src/Accesibilidad.Web -c Release -o /publicado

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app

# curl solo para la comprobacion de salud. La imagen de tiempo de ejecucion no trae ningun
# cliente HTTP, y sin el la unica comprobacion posible era preguntarle a dotnet por si
# mismo, que responde igual de bien con la aplicacion caida.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=build /publicado .

# Escucha en todas las interfaces: dentro del contenedor, localhost solo seria alcanzable
# desde el propio contenedor.
ENV ASPNETCORE_URLS=http://0.0.0.0:8080 \
    Asr__Motor=whisper \
    Asr__Url=http://asr:5601
EXPOSE 8080

# Se consulta el endpoint real, no el runtime. `dotnet --info` respondia correctamente con
# la aplicacion muerta, de modo que el contenedor se declaraba sano mientras el aula se
# quedaba sin subtitulos: una comprobacion que no puede fallar no comprueba nada.
#
# El puerto se extrae de ASPNETCORE_URLS, que es la unica variable que llega al contenedor
# y la que decide donde escucha la aplicacion. Usar PUERTO_APP aqui no valdria: esa vive en
# el .env del anfitrion, compose la interpola al construir ASPNETCORE_URLS y nunca entra en
# el contenedor, de modo que la comprobacion se quedaria mirando el 8080 mientras la
# aplicacion sirve en otro puerto.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${ASPNETCORE_URLS##*:}/salud" || exit 1

ENTRYPOINT ["dotnet", "Accesibilidad.Web.dll"]
