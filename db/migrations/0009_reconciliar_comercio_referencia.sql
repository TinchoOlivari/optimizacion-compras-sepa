-- 0009_reconciliar_comercio_referencia.sql

ALTER TABLE IF EXISTS carrito_distribuido
DROP COLUMN IF EXISTS comercio_referencia_nombre,
DROP COLUMN IF EXISTS comercio_referencia_direccion;
