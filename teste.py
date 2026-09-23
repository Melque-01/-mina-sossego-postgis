import os
import psycopg

from backend.config import DSN, DSN_FALLBACK

CANDS = [
    os.environ.get("DB_DSN", ""),
    DSN,
    DSN_FALLBACK,
    "host=localhost dbname=sossego_desmate user=postgres password=postgres_dev",
]
for d in CANDS:
    if not d:
        continue
    try:
        with psycopg.connect(d, connect_timeout=3) as c:
            from backend.config import mask_dsn

            print("OK", c.execute("SELECT postgis_version()").fetchone()[0], "via", mask_dsn(d))
            break
    except Exception as e:
        print("FALHOU", d.split(" ")[0], str(e)[:100])
