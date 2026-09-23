"""Autenticação isolada - tokens, hash, perfis.

Segurança:
 - Tokens com expiração (TTL)
 - Hash continua sha256 p/ compatibilidade com gerar_base.py,
   mas encapsulado aqui p/ trocar por bcrypt/argon2 sem mexer no resto.
 - Nenhum handler HTTP importa hashlib/secrets direto; passa por aqui.
"""
import hashlib
import secrets
import time
from .config import TOKEN_TTL_SEGUNDOS
from .db import fetch_one

# token -> {"login": str, "perfil": str, "exp": float}
TOKENS: dict[str, dict] = {}

def sha(s: str) -> str:
    """Hash senha - trocar por bcrypt quando possível."""
    return hashlib.sha256(s.encode()).hexdigest()

def criar_token(login: str, perfil: str) -> str:
    tok = secrets.token_hex(24)  # 48 chars hex - maior que antes
    TOKENS[tok] = {"login": login, "perfil": perfil, "exp": time.time() + TOKEN_TTL_SEGUNDOS}
    return tok

def validar_token(token: str):
    dados = TOKENS.get(token)
    if not dados:
        return None
    if dados["exp"] < time.time():
        TOKENS.pop(token, None)
        return None
    return {"login": dados["login"], "perfil": dados["perfil"]}

def extrair_bearer(headers) -> dict | None:
    auth = headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    tok = auth[7:].strip()
    if not tok:
        return None
    return validar_token(tok)

def autenticar(login: str, senha: str):
    """Verifica no banco; retorna (login, perfil) ou None."""
    if not login or not senha:
        return None
    row = fetch_one(
        "SELECT login, perfil FROM usuarios WHERE login=%s AND senha_hash=%s",
        (login, sha(senha)),
    )
    if not row:
        return None
    return {"login": row[0], "perfil": row[1]}

def pode_cadastrar(perfil: str) -> bool:
    return perfil in ("professor", "admin")

def limpar_expirados():
    agora = time.time()
    expirados = [k for k, v in TOKENS.items() if v["exp"] < agora]
    for k in expirados:
        TOKENS.pop(k, None)
