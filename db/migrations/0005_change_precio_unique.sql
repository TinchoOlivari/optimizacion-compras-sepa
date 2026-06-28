-- 0005_change_precio_unique.sql

BEGIN;

DELETE FROM precio
WHERE id IN (
    SELECT id
    FROM (
        SELECT
            id,
            ROW_NUMBER() OVER (
                PARTITION BY producto_id, sucursal_id
                ORDER BY fecha_vigencia DESC, id DESC
            ) AS rn
        FROM precio
    ) ranked
    WHERE ranked.rn > 1
);

ALTER TABLE precio DROP CONSTRAINT IF EXISTS uq_precio_natural;

ALTER TABLE precio
    ADD CONSTRAINT uq_precio_natural UNIQUE (producto_id, sucursal_id);

COMMIT;
