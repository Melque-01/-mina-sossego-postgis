"""Gera base Sossego + desmate sintético compatível MapBiomas.
Uso:
  source .venv/bin/activate
  cp .env.example .env  # ajuste DB_PASS se necessário
  python gerar_base.py                      # usa DB_DSN do env ou defaults dev
  python gerar_base.py --dsn "host=... ..." # DSN manual

O sintético serve p/ desenvolver frontend/APIs sem baixar GBs.
Trocar pelo real: QGIS -> exportar shape -> shp2pgsql -> tabela desmate
(ver .md/ROTEIRO_QGIS.md). Números QGIS viram gabarito da defesa.
"""
import hashlib
import os
import sys

try:
    import psycopg
except ImportError:
    print("Ative a venv: source .venv/bin/activate && pip install 'psycopg[binary]'")
    sys.exit(1)

# Mina do Sossego - Complexo Sequeirinho/Sossego, Canaã dos Carajás-PA
# Ponto central da cava (ajustável no QGIS; WGS84).
MINA = {
    "nome": "Mina do Sossego",
    "operadora": "Vale S.A.",
    "municipio": "Canaã dos Carajás-PA",
    "substancia": "Cobre",
    "lon": -50.0790,
    "lat": -6.4325,
}

_DB_USER = os.getenv("DB_USER", "ubunto")
_DB_PASS = os.getenv("DB_PASS", "dev_only_change_me")
_DB_NAME = os.getenv("DB_NAME", "sossego_desmate")
_DB_HOST = os.getenv("DB_HOST", "localhost")

CANDIDATOS_DSN = [
    os.environ.get("DB_DSN", ""),
    f"host={_DB_HOST} port=15432 dbname={_DB_NAME} user={_DB_USER} password={_DB_PASS}",  # host -> VM via NAT
    f"host={_DB_HOST} dbname={_DB_NAME} user={_DB_USER} password={_DB_PASS}",  # dentro da VM
    "host=localhost dbname=sossego_desmate user=postgres password=postgres_dev",  # dev local alternativo
]


def escolher_dsn(dsn_manual=""):
    if dsn_manual:
        return dsn_manual
    for d in CANDIDATOS_DSN:
        if not d:
            continue
        try:
            with psycopg.connect(d, connect_timeout=3) as c:
                c.execute("SELECT 1")
            from backend.config import mask_dsn

            print(f"DSN ok: {mask_dsn(d)}")
            return d
        except Exception as e:
            print(f"DSN falhou ({d.split(' ')[0]} ...): {str(e)[:90]}")
    print("Nenhum DSN funcionou. Suba a VM ou crie o banco (ver setup_vm.sh / README).")
    sys.exit(1)


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def main():
    dsn_manual = ""
    if "--dsn" in sys.argv:
        dsn_manual = sys.argv[sys.argv.index("--dsn") + 1]
    dsn = escolher_dsn(dsn_manual)

    # senha demo — troca em produção via DB_PASS / hash bcrypt
    DEMO_PASS = os.getenv("DEMO_PASS", "dev_only_change_me")

    with psycopg.connect(dsn) as conn:
        with open("schema.sql", encoding="utf-8") as f:
            conn.execute(f.read())
        print("schema.sql aplicado.")

        # 1. Mina
        conn.execute(
            """INSERT INTO mina (nome, operadora, municipio, substancia, lon, lat, geom)
               VALUES (%s,%s,%s,%s,%s,%s,
                 ST_Transform(ST_SetSRID(ST_MakePoint(%s,%s),4326),31982))
               RETURNING id""",
            (MINA["nome"], MINA["operadora"], MINA["municipio"], MINA["substancia"], MINA["lon"], MINA["lat"], MINA["lon"], MINA["lat"]),
        )
        mina_id = conn.execute("SELECT id FROM mina WHERE nome=%s", (MINA["nome"],)).fetchone()[0]

        # 2. Buffers 1/5/10 km
        for raio in (1, 5, 10):
            conn.execute(
                """INSERT INTO buffer_entorno (mina_id, raio_km, geom)
                   SELECT %s, %s, ST_Buffer(geom, %s)
                   FROM mina WHERE id=%s
                   ON CONFLICT (mina_id, raio_km) DO UPDATE SET geom=EXCLUDED.geom""",
                (mina_id, raio, raio * 1000, mina_id),
            )
        print("mina + buffers 1/5/10km ok.")

        # 3. Desmate sintético (seed fixa p/ turma reproduzir)
        # Anos justificáveis: 2008 pré-expansão, 2015 operação plena, 2023 recente.
        conn.execute("SELECT setseed(0.42)")
        conn.execute("DELETE FROM desmate")
        # (ano, classe, n_patches, raio_medio_m, centro_lon_offset, centro_lat_offset)
        planos = [
            (2008, "mineracao", 14, 250, 0.004, 0.002),
            (2008, "pastagem", 22, 180, 0.030, -0.025),
            (2008, "outros", 10, 150, -0.025, 0.020),
            (2015, "mineracao", 26, 250, 0.005, 0.002),
            (2015, "pastagem", 48, 220, 0.035, -0.030),
            (2015, "outros", 18, 170, -0.030, 0.025),
            (2023, "mineracao", 38, 250, 0.006, 0.003),
            (2023, "pastagem", 85, 260, 0.040, -0.035),
            (2023, "outros", 30, 190, -0.035, 0.030),
        ]
        total = 0
        for ano, classe, n, raio_m, dlon, dlat in planos:
            if classe == "mineracao":
                continue  # mineracao vira area unica recortada abaixo
            spread = 0.09
            conn.execute(
                """
                INSERT INTO desmate (ano, classe, fonte, geom)
                SELECT %s, %s, 'MapBiomas-sintetico',
                  ST_Multi(
                    ST_Transform(
                      ST_Buffer(
                        ST_SetSRID(ST_MakePoint(%s + (random()-0.5)*%s,
                                               %s + (random()-0.5)*%s), 4326)::geography,
                        %s * (0.6 + random()*0.8)
                      )::geometry, 31982)
                  )
                FROM generate_series(1, %s)
                """,
                (ano, classe, MINA["lon"] + dlon, spread, MINA["lat"] + dlat, spread, raio_m, n),
            )
            total += n
        # area unica recortada de mineracao (cava) - 1 poligono por ano, 100% dentro do 1km
        # 2008 bem menor para demo ficar obvio (45 ha vs 252 ha)
        for ano, raios in [(2008, [380]), (2015, [750, 480, 320]), (2023, [880, 620, 440, 360])]:
            offsets = [(0, 0), (350, 180), (-180, -320), (120, -520)][: len(raios)]
            buffers = " , ".join([f"ST_Buffer(ST_Translate(m.geom,{dx},{dy}),{r})" for (dx, dy), r in zip(offsets, raios)])
            conn.execute(
                f"""
                INSERT INTO desmate (ano, classe, fonte, geom, area_ha)
                SELECT %s, 'mineracao', 'MapBiomas-sintetico',
                  ST_Multi(ST_Intersection(ST_Union(ARRAY[{buffers}]), (SELECT ST_Buffer(geom,1000) FROM mina LIMIT 1))),
                  ROUND((ST_Area(ST_Intersection(ST_Union(ARRAY[{buffers}]), (SELECT ST_Buffer(geom,1000) FROM mina LIMIT 1)))/10000)::numeric,2)
                FROM mina m
            """,
                (ano,),
            )
            total += 1
        # area_ha para pastagem/outros
        conn.execute("UPDATE desmate SET area_ha = ROUND((ST_Area(geom)/10000.0)::numeric,2) WHERE area_ha IS NULL")
        print(f"desmate sintético: {total} patches.")

        # 4. Usuários (login do frontend) — senha demo via env DEMO_PASS
        conn.execute(
            "INSERT INTO usuarios (login, senha_hash, perfil) VALUES (%s,%s,%s) "
            "ON CONFLICT (login) DO UPDATE SET senha_hash=EXCLUDED.senha_hash",
            ("admin", sha(DEMO_PASS), "professor"),
        )
        conn.execute(
            "INSERT INTO usuarios (login, senha_hash, perfil) VALUES (%s,%s,%s) "
            "ON CONFLICT (login) DO UPDATE SET senha_hash=EXCLUDED.senha_hash",
            ("aluno", sha(DEMO_PASS), "aluno"),
        )
        conn.commit()

        n = conn.execute("SELECT count(*) FROM desmate").fetchone()[0]
        print(f"OK: {n} polígonos desmate.")
        for r in conn.execute("SELECT raio_km, ano, SUM(ha) FROM vw_serie_buffer GROUP BY 1,2 ORDER BY 1,2").fetchall():
            print(f"  buffer {r[0]}km ano {r[1]} -> {r[2]} ha")
        print(f"Logins demo: admin/aluno com senha de DEMO_PASS (default dev_only_change_me)")


if __name__ == "__main__":
    main()
