-- seed/bandera_logos.sql
-- Asigna url_logo a las banderas. Ejecutar después de 0006_bandera.sql.
-- Los archivos de logo van en apps/web/public/logos/banderas/{nombre}.png

UPDATE bandera SET url_logo = 'logos/banderas/disco.png'   WHERE LOWER(nombre) = 'disco';
UPDATE bandera SET url_logo = 'logos/banderas/jumbo.png'   WHERE LOWER(nombre) = 'jumbo';
UPDATE bandera SET url_logo = 'logos/banderas/vea.png'     WHERE LOWER(nombre) = 'vea';
UPDATE bandera SET url_logo = 'logos/banderas/coto.png'    WHERE LOWER(nombre) = 'coto';
UPDATE bandera SET url_logo = 'logos/banderas/carrefour.png' WHERE LOWER(nombre) = 'carrefour';
UPDATE bandera SET url_logo = 'logos/banderas/dia.png'     WHERE LOWER(nombre) = 'dia';
UPDATE bandera SET url_logo = 'logos/banderas/chango.png'  WHERE LOWER(nombre) = 'chango mas' OR LOWER(nombre) = 'changomas';
