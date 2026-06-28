# Optimización de compras con datos abiertos del SEPA

## Qué hay adentro

- `apps/web` — el frontend, React + TypeScript con Vite
- `apps/api` — el backend, FastAPI
- `apps/ingesta` — el proceso que carga los datos del SEPA a la base
- `packages/shared` — tipos y enums que comparten web y api
- `db/` — las migraciones SQL y unos datos de ejemplo
- `infra/` — el docker-compose y la config

El stack es Node 22, Python 3.13, Postgres 17 con PostGIS, y OSRM.

## Cómo correr el proyecto

Lo único que necesitás es tener Docker instalado.

```bash
cp infra/.env.example .env
docker compose -f infra/docker-compose.yml up --build
```

Con eso levanta la base (Postgres + PostGIS), corre las migraciones una sola vez y arranca la API
y la web. La primera vez tarda un rato porque tiene que construir todo.

Después entrás a:

- la web en http://localhost:3000
- la api en http://localhost:8000 (la doc está en /docs)

Para chequear que la api esté viva: `curl http://localhost:8000/api/v1/health` te tiene que
devolver `{"status":"ok","db":"ok"}`.

Para apagar todo: `docker compose -f infra/docker-compose.yml down`.

## Cómo hacer la ingesta de datos

La ingesta no arranca sola con el resto, se corre aparte cuando la querés. Tarda más o menos 20 minutos.

```bash
docker compose -f infra/docker-compose.yml --profile tools build ingesta
docker compose -f infra/docker-compose.yml --profile tools run --rm ingesta
```

Hay dos maneras de que tome los datos, depende de cómo tengas el `.env`:

- Si `SEPA_PORTAL_URL` está cargada, se conecta al portal y baja solo el último ZIP que publicó el SEPA.
- Si `SEPA_PORTAL_URL` está vacía, lee los paquetes que dejes en la carpeta `SEPA/` de la raíz del repo (esa carpeta no viene incluida, fue utilizada cuando se descargaba el .zip a mano con los precios del SEPA).

Correr la ingesta varias veces no rompe nada: nunca borra ni duplica, solo actualiza los precios.
Si corrés el mismo lote diez veces queda igual que correrlo una.

## OSRM (el ruteo, opcional)

Para que calcule distancias reales por calle y no en línea recta uso OSRM. No arranca por defecto porque hay que bajar el mapa de Argentina y procesarlo una vez, y pesa: el mapa son unos 400 MB y
procesado queda en ~3 GB.

```bash
# 1. bajar el mapa de Argentina
curl -L -o infra/osm/argentina-latest.osm.pbf https://download.geofabrik.de/south-america/argentina-latest.osm.pbf

# 2. procesarlo (esto se hace una sola vez)
docker run --rm --platform linux/amd64 -v "$(pwd)/infra/osm:/data" ghcr.io/project-osrm/osrm-backend:v6.0.0 osrm-extract -p /opt/car.lua /data/argentina-latest.osm.pbf
docker run --rm --platform linux/amd64 -v "$(pwd)/infra/osm:/data" ghcr.io/project-osrm/osrm-backend:v6.0.0 osrm-partition /data/argentina-latest
docker run --rm --platform linux/amd64 -v "$(pwd)/infra/osm:/data" ghcr.io/project-osrm/osrm-backend:v6.0.0 osrm-customize /data/argentina-latest

# 3. levantarlo
docker compose -f infra/docker-compose.yml --profile geo up -d osrm
```

Un detalle: en mi Mac el contenedor escucha en el 5000 pero afuera se publica en el 5001. Adentro
de Docker la api le habla por `http://osrm:5000`.

## Base de datos

El esquema se aplica con archivos SQL planos que están en `db/migrations`. 

## Comandos para correr los chequeos

```bash
# api e ingesta (Python)
ruff check . && black --check . && mypy . && pytest

# web (desde la raíz)
npm run lint:web && npm run typecheck:web && npm run test:web
```