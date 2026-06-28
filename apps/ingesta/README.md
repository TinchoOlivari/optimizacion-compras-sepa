# Ingesta SEPA

Proceso batch para almacenamiento diario SEPA con idempotencia por lote y filtro de EAN válido.

## Variables de entorno

- `DATABASE_URL`: conexión PostgreSQL.
- `SEPA_PORTAL_URL`: URL base CKAN (`https://datos.produccion.gob.ar`). Si está vacía, corre en modo local leyendo directorios en `SEPA_DOWNLOAD_DIR` y `SEPA_DOWNLOAD_DIR/local`.
- `CKAN_DATASET_ID`: dataset CKAN (default `sepa-precios`).
- `SEPA_DOWNLOAD_DIR`: directorio de ZIPs / extracts (`/data/sepa` en Docker, escribible).
- `SEPA_FECHA_LOTE`: opcional en modo local (ISO `YYYY-MM-DD`). En modo CKAN se ignora: se descarga el último ZIP publicado y su fecha define el lote.

## Ejecutar

```bash
# stack completo
docker compose -f infra/docker-compose.yml up --build

# rebuild + ingesta one-shot (requerido tras cambios en apps/ingesta)
docker compose -f infra/docker-compose.yml --profile tools build ingesta
docker compose -f infra/docker-compose.yml --profile tools run --rm ingesta
```

## Qué datos persisten y cuáles no

El pipeline **nunca borra datos**. Cada tabla usa exclusivamente `INSERT ... ON CONFLICT DO UPDATE` (UPSERT). El
comportamiento por entidad:

| Entidad | Clave de conflicto | ¿Se borra? | ¿Qué pasa al re-ingerir el mismo lote? |
|---|---|---|---|
| **Comercio** | `cuit` | No | Actualiza `razon_social` y `marca` si cambiaron |
| **Sucursal** | `(sepa_id_comercio, sepa_id_bandera, sepa_id_sucursal)` | No | Actualiza todos los campos si algún valor difiere |
| **Producto** | `codigo_ean` | No | Actualiza `nombre`, `marca` y `presentacion` si cambiaron |
| **Precio** | `(producto_id, sucursal_id)` | No | Actualiza `valor` y `fecha_vigencia` si el precio cambió. Solo existe 1 precio por producto+sucursal |
| **Lote ingesta** | `(fecha_lote, origen)` | No | Reinicia contadores y errores del lote, preserva el `id` |

**Consecuencia práctica**: cada par producto-sucursal tiene exactamente un precio (el ultimo conocido).
Re-ingerir 100 veces el mismo archivo solo actualiza valores en su lugar. Si el SEPA publica un ZIP
mas reciente, los precios se actualizan sin acumular historial — el almacenamiento es constante en
el tiempo.

Las tablas temporales (`tmp_comercio`, `tmp_sucursal`, `tmp_precio`, `tmp_producto`) se crean con
`ON COMMIT DROP` y desaparecen al hacer commit; son auxiliares para el COPY masivo y no afectan los
datos persistentes.