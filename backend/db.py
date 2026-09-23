"""db.py — conexão Postgres/PostGIS. Único módulo que importa psycopg."""
import psycopg

from .config import DSN, DSN_FALLBACK, mask_dsn

try:
    import psycopg  # noqa: F401
except ImportError:
    raise SystemExit("Ative a venv: source .venv/bin/activate && pip install 'psycopg[binary]'")

# Tenta DSN principal, se falhar usa fallback (VM via NAT 15432)
def _test(dsn: str) -> bool:
    try:
        with psycopg.connect(dsn, connect_timeout=3) as c:
            c.execute("SELECT 1")
        return True
    except Exception:
        return False

if _test(DSN):
    DSN_OK = DSN
    print(f"[db] Banco ok: {mask_dsn(DSN_OK)}")
elif _test(DSN_FALLBACK):
    DSN_OK = DSN_FALLBACK
    print(f"[db] Banco ok (fallback): {mask_dsn(DSN_OK)}")
else:
    DSN_OK = DSN
    print("[db] Sem banco. Rode setup_vm.sh / gerar_base.py.")

# exportado para api/handlers
DSN = DSN_OK


def get_conn():
    return psycopg.connect(DSN)


def fetch_one(sql, params=()):
    with get_conn() as c:
        return c.execute(sql, params).fetchone()


def fetch_all(sql, params=()):
    with get_conn() as c:
        return c.execute(sql, params).fetchall()


def execute_commit(sql, params=()):
    with get_conn() as c:
        row = c.execute(sql, params).fetchone()
        c.commit()
        return row
