"""config.py — constantes e DSN. Único lugar que lê env."""
import os

# Validação
CLASSES_VALIDAS = {"mineracao", "pastagem", "outros"}
BUFFERS_VALIDOS = {1, 5, 10}
LIMITE_MIN, LIMITE_MAX = 1, 5000
COORD_LON_MIN, COORD_LON_MAX = -75, -30
COORD_LAT_MIN, COORD_LAT_MAX = -35, 6

# Auth
TOKEN_TTL_SEGUNDOS = 8 * 3600

# Banco — tudo via env. Fallback dev local (VM descartável).
# Em produção defina DB_DSN no .env / secrets — nunca commite .env
_DB_USER = os.getenv("DB_USER", "ubunto")
_DB_PASS = os.getenv("DB_PASS", "dev_only_change_me")
_DB_NAME = os.getenv("DB_NAME", "sossego_desmate")
_DB_HOST = os.getenv("DB_HOST", "localhost")

DSN = os.getenv("DB_DSN", f"host={_DB_HOST} dbname={_DB_NAME} user={_DB_USER} password={_DB_PASS}")
DSN_FALLBACK = os.getenv(
    "DB_DSN_FALLBACK", f"host={_DB_HOST} port=15432 dbname={_DB_NAME} user={_DB_USER} password={_DB_PASS}"
)


def mask_dsn(dsn: str) -> str:
    if "password" in dsn:
        return dsn.split("password")[0] + "password=***"
    return dsn[:40] + "***"
