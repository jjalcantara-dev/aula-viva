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
COPY --from=build /publicado .

# Escucha en todas las interfaces: dentro del contenedor, localhost solo seria alcanzable
# desde el propio contenedor.
ENV ASPNETCORE_URLS=http://0.0.0.0:8080 \
    Asr__Motor=whisper \
    Asr__Url=http://asr:5601
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["dotnet", "--info"]

ENTRYPOINT ["dotnet", "Accesibilidad.Web.dll"]
