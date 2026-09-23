-- ============================================================
-- Mina do Sossego x Desmatamento (MapBiomas) - schema PostGIS
-- SRID 31982 (UTM 22S / SIRGAS 2000) p/ área em metros.
-- Frontend usa 4326 (Leaflet). Conversão via ST_Transform.
-- Roda na VM: psql -h localhost -U $DB_USER -d $DB_NAME -f schema.sql  (ver .env.example)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS desmate CASCADE;
DROP TABLE IF EXISTS buffer_entorno CASCADE;
DROP TABLE IF EXISTS mina CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- Mina real de referência (ponto ajustável no QGIS)
CREATE TABLE mina (
  id serial PRIMARY KEY,
  nome text NOT NULL,
  operadora text NOT NULL DEFAULT 'Vale S.A.',
  municipio text NOT NULL DEFAULT 'Canaã dos Carajás-PA',
  substancia text NOT NULL DEFAULT 'Cobre',
  lon double precision NOT NULL,
  lat double precision NOT NULL,
  geom geometry(Point, 31982) NOT NULL
);

-- Buffers do "entorno": 1km direto, 5km indireto, 10km controle
CREATE TABLE buffer_entorno (
  id serial PRIMARY KEY,
  mina_id integer NOT NULL REFERENCES mina(id) ON DELETE CASCADE,
  raio_km integer NOT NULL,
  geom geometry(Polygon, 31982) NOT NULL,
  UNIQUE (mina_id, raio_km)
);

-- Desmate vetorizado do MapBiomas (um polígono = um patch desmatado)
-- classe: mineracao | pastagem | outros  (espelha legenda MapBiomas simplificada)
CREATE TABLE desmate (
  id serial PRIMARY KEY,
  ano integer NOT NULL CHECK (ano BETWEEN 1985 AND 2030),
  classe text NOT NULL CHECK (classe IN ('mineracao','pastagem','outros')),
  fonte text NOT NULL DEFAULT 'MapBiomas',
  area_ha numeric(12,2),
  geom geometry(MultiPolygon, 31982) NOT NULL
);

-- Login do frontend
CREATE TABLE usuarios (
  id serial PRIMARY KEY,
  login text UNIQUE NOT NULL,
  senha_hash text NOT NULL, -- sha256 hex
  perfil text NOT NULL DEFAULT 'aluno'
);

CREATE INDEX mina_geom_idx ON mina USING GIST (geom);
CREATE INDEX buffer_geom_idx ON buffer_entorno USING GIST (geom);
CREATE INDEX desmate_geom_idx ON desmate USING GIST (geom);
CREATE INDEX desmate_ano_idx ON desmate (ano);
CREATE INDEX desmate_classe_idx ON desmate (classe);

-- Vista pronta p/ o dashboard: ha desmatado por buffer x ano x classe
CREATE OR REPLACE VIEW vw_serie_buffer AS
SELECT b.raio_km, d.ano, d.classe,
  COUNT(*) AS n_patches,
  ROUND((SUM(ST_Area(ST_Intersection(b.geom, d.geom))) / 10000.0)::numeric, 2) AS ha
FROM buffer_entorno b
JOIN desmate d ON ST_Intersects(b.geom, d.geom)
GROUP BY b.raio_km, d.ano, d.classe;
