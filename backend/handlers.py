"""handlers.py — lógica das rotas. Único lugar com regras de negócio.
Usado por backend/api.py e por frontend.py (fallback).
Cada função retorna (dados, status).
"""
from urllib.parse import parse_qs

from . import auth, geo


def health():
    from .config import mask_dsn
    from .db import DSN
    return {"ok": True, "dsn": mask_dsn(DSN)}, 200


def login(body: dict):
    login = (body or {}).get("login", "")
    senha = (body or {}).get("senha", "")
    if not login or not senha:
        return {"erro": "Informe login e senha"}, 400
    user = auth.autenticar(login, senha)
    if not user:
        return {"erro": "Login ou senha invalidos"}, 401
    tok = auth.criar_token(user["login"], user["perfil"])
    return {"token": tok, "login": user["login"], "perfil": user["perfil"]}, 200


def perfil(headers):
    user = auth.extrair_bearer(headers)
    if not user:
        return {"erro": "Nao autenticado"}, 401
    return user, 200


def _requer_auth(headers):
    user = auth.extrair_bearer(headers)
    if not user:
        return None, ({"erro": "Nao autenticado"}, 401)
    return user, None


def mina(headers):
    user, err = _requer_auth(headers)
    if err:
        return err
    try:
        return geo.get_mina(), 200
    except Exception:
        return {"erro": "Erro interno"}, 500


def buffers(headers):
    user, err = _requer_auth(headers)
    if err:
        return err
    try:
        return geo.get_buffers(), 200
    except Exception:
        return {"erro": "Erro interno"}, 500


def desmate_get(headers, query_string: str):
    user, err = _requer_auth(headers)
    if err:
        return err
    q = parse_qs(query_string)
    ano = q.get("ano", [None])[0]
    classe = q.get("classe", [None])[0]
    buffer = q.get("buffer", [None])[0]
    limite = q.get("limite", ["500"])[0]
    erro = geo.validar_filtros_desmate(ano, classe, buffer, limite)
    if erro:
        return {"erro": erro}, 400
    try:
        return geo.get_desmate(ano, classe, buffer, limite), 200
    except Exception:
        return {"erro": "Erro interno"}, 500


def serie(headers):
    user, err = _requer_auth(headers)
    if err:
        return err
    try:
        return geo.get_serie(), 200
    except Exception:
        return {"erro": "Erro interno"}, 500


def resumo(headers):
    user, err = _requer_auth(headers)
    if err:
        return err
    try:
        return geo.get_resumo(), 200
    except Exception:
        return {"erro": "Erro interno"}, 500


def desmate_post(headers, body: dict):
    user, err = _requer_auth(headers)
    if err:
        return err
    if not auth.pode_cadastrar(user.get("perfil", "")):
        return {"erro": "Apenas professor pode cadastrar"}, 403
    dados, erro = geo.validar_insert(body or {})
    if erro:
        return {"erro": erro}, 400
    try:
        nid = geo.inserir_desmate(dados)
        return {"id": nid}, 201
    except Exception:
        return {"erro": "Erro ao inserir"}, 500


# Dispatcher simples — evita repetir ifs no api.py e frontend.py
ROUTES = {
    ("GET", "/api/health"): lambda h, q, b: health(),
    ("GET", "/api/login"): lambda h, q, b: ({"erro": "Use POST"}, 405),
    ("POST", "/api/login"): lambda h, q, b: login(b),
    ("GET", "/api/perfil"): lambda h, q, b: perfil(h),
    ("GET", "/api/mina"): lambda h, q, b: mina(h),
    ("GET", "/api/buffers"): lambda h, q, b: buffers(h),
    ("GET", "/api/desmate"): lambda h, q, b: desmate_get(h, q),
    ("GET", "/api/serie"): lambda h, q, b: serie(h),
    ("GET", "/api/resumo"): lambda h, q, b: resumo(h),
    ("POST", "/api/desmate"): lambda h, q, b: desmate_post(h, b),
}


def dispatch(method: str, path: str, headers, query_string: str = "", body: dict | None = None):
    """Retorna (dados, status) ou None se rota não existe."""
    fn = ROUTES.get((method, path))
    if fn:
        return fn(headers, query_string, body)
    # 404 para /api/*, None para não-api
    if path.startswith("/api/"):
        return {"erro": "Nao encontrado"}, 404
    return None
