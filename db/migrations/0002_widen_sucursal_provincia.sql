-- 0002_widen_sucursal_provincia.sql

ALTER TABLE IF EXISTS sucursal
    ALTER COLUMN provincia TYPE VARCHAR(64);
