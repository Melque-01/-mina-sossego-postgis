"""Regras de negócio geoespacial - todas as queries PostGIS isoladas aqui.

Nenhum SQL é montado via f-string com input do usuário; tudo parametrizado.
Validação de entrada fica aqui também, não no servidor HTTP.
"""
import json
from .config import CLASSES_VALIDAS, BUFFERS_VALIDOS, LIMITE_MIN, LIMITE_MAX
from .config import COORD_LON_MIN, COORD_LON_MAX, COORD_LAT_MIN, COORD_LAT_MAX
from .db import fetch_one, fetch_all, execute_commit

# ---------- validações ----------

def validar_filtros_desmate(ano, classe, buffer, limite):
    if limite is not None:
        if not str(limite).isdigit() or not (LIMITE_MIN <= int(limite) <= LIMITE_MAX):
            return "Limite invalido"
    if classe and classe not in CLASSES_VALIDAS:
        return "Classe invalida"
    if ano and not str(ano).isdigit():
        return "Ano invalido"
    if buffer and (not str(buffer).isdigit() or int(buffer) not in BUFFERS_VALIDOS):
        return "Buffer invalido (1,5,10)"
    return None

def validar_insert(payload: dict):
    try:
        ano = int(payload.get("ano", 0))
        classe = payload.get("classe", "")
        lon = float(payload.get("lon", 0))
        lat = float(payload.get("lat", 0))
        raio_m = float(payload.get("raio_m", 150))
    except Exception:
        return None, "Dados invalidos"
    if classe not in CLASSES_VALIDAS or not (1985 <= ano <= 2030):
        return None, "Dados invalidos"
    if not (COORD_LON_MIN < lon < COORD_LON_MAX and COORD_LAT_MIN < lat < COORD_LAT_MAX):
        return None, "Coordenada fora do Brasil"
    if not (10 <= raio_m <= 5000):
        return None, "raio_m invalido (10-5000)"
    return {"ano": ano, "classe": classe, "lon": lon, "lat": lat, "raio_m": raio_m}, None

# ---------- queries ----------

def get_mina():
    sql = """SELECT json_build_object('type','FeatureCollection','features',
                      COALESCE(json_agg(ST_AsGeoJSON(t.*)::json),'[]'::json))
             FROM (SELECT id, nome, operadora, municipio, substancia,
                          ST_Transform(geom,4326) AS geom FROM mina) t"""
    row = fetch_one(sql)
    res = row[0] if row else None
    return json.loads(res) if isinstance(res, str) else res

def get_buffers():
    sql = """SELECT json_build_object('type','FeatureCollection','features',
                      COALESCE(json_agg(ST_AsGeoJSON(t.*)::json),'[]'::json))
             FROM (SELECT id, mina_id, raio_km,
                          ROUND((ST_Area(geom)/10000.0)::numeric,2) AS area_ha,
                          ST_Transform(geom,4326) AS geom
                   FROM buffer_entorno ORDER BY raio_km) t"""
    row = fetch_one(sql)
    res = row[0] if row else None
    return json.loads(res) if isinstance(res, str) else res

def get_desmate(ano=None, classe=None, buffer=None, limite=500):
    sql = """
            SELECT json_build_object('type','FeatureCollection','features',
              COALESCE(json_agg(ST_AsGeoJSON(t.*)::json),'[]'::json))
            FROM (
              SELECT d.id, d.ano, d.classe, d.fonte, d.area_ha,
                     ST_Transform(d.geom,4326) AS geom
              FROM desmate d
              LEFT JOIN buffer_entorno b
                ON b.raio_km = %s::int AND ST_Intersects(b.geom, d.geom)
              WHERE (%s::text IS NULL OR d.classe = %s)
                AND (%s::text IS NULL OR d.ano = %s::int)
                AND (%s::text IS NULL OR b.id IS NOT NULL)
              ORDER BY d.ano, d.id LIMIT %s
            ) t"""
    row = fetch_one(sql, (buffer, classe, classe, ano, ano, buffer, int(limite)))
    res = row[0] if row else None
    return json.loads(res) if isinstance(res, str) else res

def get_serie():
    linhas = fetch_all("SELECT raio_km, ano, classe, n_patches, ha FROM vw_serie_buffer ORDER BY raio_km, ano, classe")
    return [{"raio_km": r[0], "ano": r[1], "classe": r[2], "n": r[3], "ha": float(r[4])} for r in linhas]

def get_resumo():
    por_ano = fetch_all("SELECT ano, COUNT(*), ROUND(SUM(area_ha)::numeric,2) FROM desmate GROUP BY ano ORDER BY ano")
    por_classe = fetch_all("SELECT classe, COUNT(*), ROUND(SUM(area_ha)::numeric,2) FROM desmate GROUP BY classe ORDER BY classe")
    buffers = fetch_all("SELECT raio_km, ROUND((ST_Area(geom)/10000.0)::numeric,2) FROM buffer_entorno ORDER BY raio_km")
    mina = fetch_one("SELECT nome, municipio, lon, lat FROM mina LIMIT 1")
    return {
        "mina": {"nome": mina[0], "municipio": mina[1], "lon": mina[2], "lat": mina[3]} if mina else None,
        "por_ano": [{"ano": r[0], "patches": r[1], "ha": float(r[2])} for r in por_ano],
        "por_classe": [{"classe": r[0], "patches": r[1], "ha": float(r[2])} for r in por_classe],
        "buffers_ha": [{"raio_km": r[0], "ha": float(r[1])} for r in buffers],
    }

def inserir_desmate(dados_validados: dict):
    sql = """INSERT INTO desmate (ano, classe, fonte, geom, area_ha)
             SELECT %s, %s, 'cadastro-manual',
               ST_Multi(ST_Transform(ST_Buffer(
                 ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, %s)::geometry,31982)),
               ROUND((%s*%s*3.14159/10000.0)::numeric,2)
             RETURNING id"""
    row = execute_commit(sql, (
        dados_validados["ano"], dados_validados["classe"],
        dados_validados["lon"], dados_validados["lat"], dados_validados["raio_m"],
        dados_validados["raio_m"], dados_validados["raio_m"],
    ))
    return row[0] if row else None
