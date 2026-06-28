-- 0003_optimizacion.sql

CREATE TABLE IF NOT EXISTS preferencias_optimizacion (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id BIGINT NOT NULL UNIQUE REFERENCES usuario (id) ON DELETE CASCADE,
    radio_km INTEGER NULL CHECK (radio_km BETWEEN 1 AND 50),
    max_paradas INTEGER NULL CHECK (max_paradas BETWEEN 1 AND 5),
    modo_preferencia preferencia_optimizacion NULL,
    ubicacion_referencia_lat DOUBLE PRECISION NULL,
    ubicacion_referencia_lon DOUBLE PRECISION NULL,
    ubicacion_referencia_direccion VARCHAR(255) NULL,
    ubicacion_referencia_modalidad modalidad_ubicacion NULL,
    ubicacion_referencia_geo GEOGRAPHY(Point, 4326) NULL
);

CREATE TABLE IF NOT EXISTS carrito_distribuido (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    carrito_id BIGINT NOT NULL REFERENCES carrito (id) ON DELETE CASCADE,
    fecha_calculo TIMESTAMPTZ NOT NULL DEFAULT now(),
    costo_total_estimado NUMERIC(12, 2) NOT NULL,
    ahorro_estimado NUMERIC(12, 2) NULL,
    vigente BOOLEAN NOT NULL DEFAULT true,
    cfg_radio_km INTEGER NOT NULL,
    cfg_max_paradas INTEGER NOT NULL,
    cfg_preferencia preferencia_optimizacion NOT NULL,
    cfg_origen_lat DOUBLE PRECISION NOT NULL,
    cfg_origen_lon DOUBLE PRECISION NOT NULL,
    cfg_origen_geo GEOGRAPHY(Point, 4326) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_distribucion_vigente_por_carrito
    ON carrito_distribuido (carrito_id) WHERE vigente = true;

CREATE TABLE IF NOT EXISTS asignacion_sucursal (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    carrito_distribuido_id BIGINT NOT NULL REFERENCES carrito_distribuido (id) ON DELETE CASCADE,
    sucursal_id BIGINT NOT NULL REFERENCES sucursal (id),
    subtotal NUMERIC(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS item_asignado (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asignacion_sucursal_id BIGINT NOT NULL REFERENCES asignacion_sucursal (id) ON DELETE CASCADE,
    item_carrito_id BIGINT NOT NULL REFERENCES item_carrito (id),
    precio_id BIGINT NOT NULL REFERENCES precio (id),
    cantidad INTEGER NOT NULL CHECK (cantidad BETWEEN 1 AND 99),
    precio_unitario NUMERIC(12, 2) NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS ruteo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    carrito_distribuido_id BIGINT NOT NULL UNIQUE REFERENCES carrito_distribuido (id) ON DELETE CASCADE,
    distancia_total_km DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS parada (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ruteo_id BIGINT NOT NULL REFERENCES ruteo (id) ON DELETE CASCADE,
    sucursal_id BIGINT NULL REFERENCES sucursal (id),
    orden INTEGER NOT NULL,
    distancia_desde_anterior_km DOUBLE PRECISION NOT NULL,
    es_origen BOOLEAN NOT NULL DEFAULT false,
    es_adicional BOOLEAN NOT NULL DEFAULT false,
    origen_lat DOUBLE PRECISION NULL,
    origen_lon DOUBLE PRECISION NULL,
    CONSTRAINT uq_parada_orden UNIQUE (ruteo_id, orden)
);
