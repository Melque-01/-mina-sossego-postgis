import json
import os
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
DEMO_PASS = os.getenv("DEMO_PASS", "dev_only_change_me")
resultados = []


def chamar(caminho, metodo="GET", corpo=None, token=None):
    url = BASE + caminho
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo)
    if dados:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}


def teste(nome, cond):
    resultados.append((nome, bool(cond)))
    print(("PASSOU " if cond else "FALHOU ") + nome)


# T0 login obrigatório
s, d = chamar("/api/mina")
teste("T0 sem token devolve 401", s == 401)
s, d = chamar("/api/login", "POST", {"login": "aluno", "senha": "errada"})
teste("T1 login errado 401", s == 401)
s, d = chamar("/api/login", "POST", {"login": "aluno", "senha": DEMO_PASS})
teste("T2 login ok 200 + token", s == 200 and "token" in d)
TOK = d.get("token", "")
# token admin para testes de escrita (POST exige perfil professor)
s_admin, d_admin = chamar("/api/login", "POST", {"login": "admin", "senha": DEMO_PASS})
TOK_ADMIN = d_admin.get("token", "") if s_admin == 200 else TOK

# T3 mina
s, d = chamar("/api/mina", token=TOK)
teste("T3 mina FeatureCollection", s == 200 and d.get("type") == "FeatureCollection")
teste("T4 mina tem 1 ponto Sossego", len(d.get("features", [])) == 1)
if d.get("features"):
    lon, lat = d["features"][0]["geometry"]["coordinates"]
    teste("T5 mina lon/lat no Pará", -51 < lon < -49 and -7.5 < lat < -5.5)

# T6 buffers
s, d = chamar("/api/buffers", token=TOK)
teste("T6 buffers 1/5/10", s == 200 and len(d.get("features", [])) == 3)

# T7 desmate respeita limite
s, d = chamar("/api/desmate?limite=5", token=TOK)
teste("T7 limite=5", s == 200 and len(d.get("features", [])) == 5)

# T8 filtro ano
s, d = chamar("/api/desmate?ano=2023&limite=2000", token=TOK)
teste("T8 filtro ano 2023", s == 200 and all(f["properties"]["ano"] == 2023 for f in d.get("features", [])))

# T9 filtro buffer
s, d = chamar("/api/desmate?buffer=1&limite=2000", token=TOK)
teste("T9 filtro buffer=1", s == 200 and len(d.get("features", [])) > 0)

# T10 classe invalida
s, d = chamar("/api/desmate?classe=dragao", token=TOK)
teste("T10 classe invalida 400", s == 400)

# T11 limite invalido
s, d = chamar("/api/desmate?limite=abc", token=TOK)
teste("T11 limite invalido 400", s == 400)

# T12 serie
s, d = chamar("/api/serie", token=TOK)
teste("T12 serie lista", s == 200 and isinstance(d, list) and len(d) >= 9)
teste("T13 serie tem ha", all("ha" in x for x in d) if isinstance(d, list) else False)

# T14 resumo
s, d = chamar("/api/resumo", token=TOK)
teste("T14 resumo por_ano+classe", s == 200 and "por_ano" in d and "por_classe" in d)

# T15 rota inexistente
s, d = chamar("/api/nao-existe", token=TOK)
teste("T15 404", s == 404)

# T16 insert (exige professor)
s, d = chamar("/api/desmate", "POST", {"ano": 2023, "classe": "pastagem", "lon": -50.05, "lat": -6.45, "raio_m": 150}, token=TOK_ADMIN)
teste("T16 POST 201 + id", s == 201 and isinstance(d.get("id"), int))
# T16b aluno não pode inserir
s, d = chamar("/api/desmate", "POST", {"ano": 2023, "classe": "pastagem", "lon": -50.05, "lat": -6.45, "raio_m": 150}, token=TOK)
teste("T16b aluno POST 403", s == 403)

# T17 insert invalido (com admin)
s, d = chamar("/api/desmate", "POST", {"ano": 2023}, token=TOK_ADMIN)
teste("T17 POST incompleto 400", s == 400)

print("\n" + "-" * 40)
ok = sum(1 for _, c in resultados if c)
print(f"RESULTADO: {ok} / {len(resultados)} testes passaram")
