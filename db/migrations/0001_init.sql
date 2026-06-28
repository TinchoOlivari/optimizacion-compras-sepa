-- 0001_init.sql

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- TIPOS ENUMERADOS

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'preferencia_optimizacion') THEN
        CREATE TYPE preferencia_optimizacion AS ENUM (
            'MENOR_PRECIO', 'MENOR_DESPLAZAMIENTO', 'BALANCEADO'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_item') THEN
        CREATE TYPE estado_item AS ENUM (
            'PENDIENTE', 'CONSEGUIDO', 'NO_ENCONTRADO', 'DESCARTADO'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_cierre') THEN
        CREATE TYPE estado_cierre AS ENUM ('COMPLETADA', 'INTERRUMPIDA');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'modalidad_ubicacion') THEN
        CREATE TYPE modalidad_ubicacion AS ENUM (
            'GEOLOCALIZACION', 'DIRECCION', 'PUNTO_EN_MAPA'
        );
    END IF;
END
$$;

-- BLOQUE 1. USUARIO Y CONFIGURACION

CREATE TABLE IF NOT EXISTS usuario (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    correo VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

-- BLOQUE 2. CATALOGO NORMALIZADO (origen SEPA)

CREATE TABLE IF NOT EXISTS comercio (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cuit VARCHAR(11) NOT NULL UNIQUE,
    razon_social VARCHAR(255) NOT NULL,
    marca VARCHAR(255) NULL
);

CREATE TABLE IF NOT EXISTS sucursal (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    comercio_id BIGINT NOT NULL REFERENCES comercio (id) ON DELETE CASCADE,
    sepa_id_comercio VARCHAR(20) NOT NULL,
    sepa_id_bandera VARCHAR(20) NOT NULL,
    sepa_id_sucursal VARCHAR(20) NOT NULL,
    nombre VARCHAR(255) NULL,
    direccion VARCHAR(255) NULL,
    localidad VARCHAR(120) NULL,
    provincia VARCHAR(10) NULL,
    latitud DOUBLE PRECISION NULL,
    longitud DOUBLE PRECISION NULL,
    geo GEOGRAPHY(Point, 4326) NULL,
    CONSTRAINT uq_sucursal_sepa UNIQUE (sepa_id_comercio, sepa_id_bandera, sepa_id_sucursal)
);

CREATE INDEX IF NOT EXISTS ix_sucursal_geo ON sucursal USING GIST (geo);

CREATE TABLE IF NOT EXISTS producto (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_ean VARCHAR(14) NOT NULL UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    marca VARCHAR(255) NULL,
    presentacion VARCHAR(255) NULL,
    url_imagen VARCHAR(500) NULL
);

CREATE INDEX IF NOT EXISTS ix_producto_nombre_trgm
    ON producto USING GIN (nombre gin_trgm_ops);

CREATE TABLE IF NOT EXISTS precio (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    producto_id BIGINT NOT NULL REFERENCES producto (id) ON DELETE CASCADE,
    sucursal_id BIGINT NOT NULL REFERENCES sucursal (id) ON DELETE CASCADE,
    valor NUMERIC(12, 2) NOT NULL CHECK (valor > 0),
    fecha_vigencia DATE NOT NULL,
    CONSTRAINT uq_precio_natural UNIQUE (producto_id, sucursal_id)
);

CREATE INDEX IF NOT EXISTS ix_precio_producto_valor ON precio (producto_id, valor);

CREATE TABLE IF NOT EXISTS lote_ingesta (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha_lote DATE NOT NULL,
    origen VARCHAR(255) NOT NULL,
    estado VARCHAR(30) NOT NULL,
    archivos_procesados INTEGER NOT NULL DEFAULT 0,
    archivos_con_error INTEGER NOT NULL DEFAULT 0,
    detalle_errores JSONB NULL,
    fecha_ejecucion TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_lote_ingesta UNIQUE (fecha_lote, origen)
);

-- BLOQUE 3. CARRITO

CREATE TABLE IF NOT EXISTS carrito (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES usuario (id) ON DELETE CASCADE,
    titulo VARCHAR(120) NULL,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_ultima_edicion TIMESTAMPTZ NOT NULL DEFAULT now(),
    activo BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS ix_carrito_usuario_edicion
    ON carrito (usuario_id, fecha_ultima_edicion DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_carrito_activo_por_usuario
    ON carrito (usuario_id) WHERE activo = true;

CREATE TABLE IF NOT EXISTS item_carrito (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    carrito_id BIGINT NOT NULL REFERENCES carrito (id) ON DELETE CASCADE,
    producto_id BIGINT NOT NULL REFERENCES producto (id),
    cantidad INTEGER NOT NULL CHECK (cantidad BETWEEN 1 AND 99),
    CONSTRAINT uq_item_carrito UNIQUE (carrito_id, producto_id)
);

-- BLOQUE 4. DISTRIBUCION (resultado del motor de optimizacion)

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
    carrito_distribuido_id BIGINT NOT NULL
        REFERENCES carrito_distribuido (id) ON DELETE CASCADE,
    sucursal_id BIGINT NOT NULL REFERENCES sucursal (id),
    subtotal NUMERIC(12, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_asignacion_distribucion
    ON asignacion_sucursal (carrito_distribuido_id);

CREATE TABLE IF NOT EXISTS item_asignado (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asignacion_sucursal_id BIGINT NOT NULL
        REFERENCES asignacion_sucursal (id) ON DELETE CASCADE,
    item_carrito_id BIGINT NOT NULL REFERENCES item_carrito (id),
    precio_id BIGINT NOT NULL REFERENCES precio (id),
    cantidad INTEGER NOT NULL CHECK (cantidad BETWEEN 1 AND 99),
    precio_unitario NUMERIC(12, 2) NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_item_asignado_asignacion
    ON item_asignado (asignacion_sucursal_id);

-- BLOQUE 5. RUTEO GEOGRAFICO

CREATE TABLE IF NOT EXISTS ruteo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    carrito_distribuido_id BIGINT NOT NULL UNIQUE
        REFERENCES carrito_distribuido (id) ON DELETE CASCADE,
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

-- BLOQUE 6. COMPRA GUIADA

CREATE TABLE IF NOT EXISTS compra_guiada (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    carrito_distribuido_id BIGINT NOT NULL
        REFERENCES carrito_distribuido (id) ON DELETE CASCADE,
    fecha_inicio TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_cierre TIMESTAMPTZ NULL,
    estado_cierre estado_cierre NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_compra_guiada_en_curso
    ON compra_guiada (carrito_distribuido_id) WHERE fecha_cierre IS NULL;

CREATE TABLE IF NOT EXISTS progreso_item (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    compra_guiada_id BIGINT NOT NULL REFERENCES compra_guiada (id) ON DELETE CASCADE,
    item_asignado_id BIGINT NOT NULL REFERENCES item_asignado (id),
    estado estado_item NOT NULL DEFAULT 'PENDIENTE',
    sucursal_actual_id BIGINT NULL REFERENCES sucursal (id),
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_progreso_item_compra_estado
    ON progreso_item (compra_guiada_id, estado);
