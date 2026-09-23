# Mina do Sossego — Desmatamento no Entorno

> **PostGIS + Python + Leaflet** · Análise geoespacial do desmatamento (MapBiomas) nos buffers de 1/5/10 km da Mina do Sossego — Canaã dos Carajás (PA).

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.6-green.svg)](https://postgis.net/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-brightgreen.svg)](https://leafletjs.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-19%2F19-brightgreen)](#testes)

Dashboard interativo que cruza **mina pontual (31982) + buffers concêntricos + patches MapBiomas** para responder: *o desmatamento no entorno é vetor da mineração ou da agropecuária?*

---

## Preview

```
┌─────────────────────────────────────────────┐
│  Mapa  Leaflet  (OSM / Esri Satélite)        │
│  ● Mina  ⬢ Buffers 1/5/10km  :: manchas     │
│  mineracao=área sólida  pastagem=círculo    │
├─────────────────────────────────────────────┤
│  KPIs:  ha desmatado  ·  % do entorno  · classe dominante │
├─────────────────────────────────────────────┤
│  Gráfico  ha por ano (1km / 5km / 10km)      │
│  Resumo por ano / classe  +  Interpretação  │
└─────────────────────────────────────────────┘
```

Login: `admin` / `aluno` · senha via `DEMO_PASS` (ver `.env.example`).

---

## Stack

| Camada | Tech |
|---|---|
| **BD** | PostgreSQL 16 + PostGIS 3.6 · SRID 31982 (UTM 22S) / 4326 no frontend |
| **Backend** | Python `http.server` puro · `psycopg[binary]` · sem ORM |
| **Frontend** | HTML + Bootstrap 5 + Leaflet 1.9 + Chart.js 4 |
| **Auth** | Bearer token em memória · TTL 8h · SHA-256 (trocar por bcrypt em prod) |

---

## Arquitetura

```
browser :8000  ──►  frontend.py (proxy /api → :8001 + serve web/)
                        │
                        ▼
                   backend/api.py :8001  ──►  backend/handlers.py (dispatch)
                                                ├─ backend/auth.py
                                                ├─ backend/geo.py  (PostGIS)
                                                └─ backend/db.py / config.py
                        │
                        ▼
                   PostgreSQL/PostGIS :5432  (ou :15432 via NAT VM)
```

*Por que 2 portas?* `api.py` é o **único** com acesso ao banco. `frontend.py` nunca toca no BD — só faz proxy. Fallback local (handlers) garante que `python servidor.py` funciona mesmo sem backend separado.

---

## Estrutura

```
.
├── backend/
│   ├── config.py      # env + constantes (sem segredo hardcoded)
│   ├── db.py          # conexão PostGIS (único import psycopg)
│   ├── auth.py        # tokens, hash, perfis
│   ├── geo.py         # queries + validações geo
│   ├── handlers.py    # dispatcher central (DRY — usado por api e frontend)
│   └── api.py         # servidor HTTP magro  — só /api/*
├── web/
│   ├── index.html     # dashboard
│   ├── login.html
│   ├── app.js         # Leaflet + Chart.js
│   └── estilo.css
├── .md/
│   └── ROTEIRO_QGIS.md  # sintético → MapBiomas real
├── PDF/               # documentação acadêmica
├── schema.sql         # modelo PostGIS 31982 + índices GIST
├── gerar_base.py      # seed: mina + buffers + desmate sintético
├── servidor.py        # launcher (sobe :8001 + :8000)
├── testes.py          # 19 testes (auth + geo)
├── setup_vm.sh        # provisionamento VM Ubuntu
├── .env.example       # template — copie para .env
└── ENTREGA.txt        # números da defesa (ha por buffer/ano)
```

Backend organizado para ser **simples**: cada arquivo < 90 linhas, sem duplicação. Lógica de rotas vive só em `handlers.py`.

---

## Quick Start

### 1. Clone + venv

```bash
git clone https://github.com/Melque-01/-mina-sossego-postgis.git
cd -mina-sossego-postgis
cp .env.example .env   # ajuste DB_PASS / DEMO_PASS se quiser
python3 -m venv .venv && source .venv/bin/activate
pip install "psycopg[binary]"
```

### 2. Banco (escolha um)

**a) VM VirtualBox (recomendado p/ lab):**

```bash
# dentro da VM Ubuntu:
chmod +x setup_vm.sh && ./setup_vm.sh
# no host:
python gerar_base.py
```

**b) Postgres local:**

```bash
createdb sossego_desmate
psql -d sossego_desmate -f schema.sql
python gerar_base.py
```

> `gerar_base.py` lê `DB_DSN` do `.env` ou monta via `DB_HOST/DB_USER/DB_PASS`. Nunca commite `.env`.

### 3. Rodar

```bash
# modo simples (frontend + fallback):
python servidor.py
# → http://localhost:8000/login.html

# modo isolado (2 terminais):
python -m backend.api   # :8001
python -m http.server 8000 --directory web  # ou python servidor.py
```

Variáveis úteis:

```bash
DEMO_PASS=minha_senha python gerar_base.py   # cria admin/aluno com essa senha
DEMO_PASS=minha_senha python testes.py       # testa com mesma senha
DB_DSN="host=... dbname=... user=... password=..." python gerar_base.py
```

---

## Variáveis de Ambiente

| Var | Default (dev) | Descrição |
|---|---|---|
| `DB_HOST` | `localhost` | Host Postgres |
| `DB_PORT` | `5432` | Porta (`15432` via NAT VM) |
| `DB_NAME` | `sossego_desmate` | Nome do banco |
| `DB_USER` | `ubunto` | Usuário |
| `DB_PASS` | `dev_only_change_me` | **Troque em produção** |
| `DB_DSN` | *(montado)* | DSN completo — sobrescreve campos acima |
| `DB_DSN_FALLBACK` | *(montado)* | Tentativa 2 (VM NAT) |
| `DEMO_PASS` | `dev_only_change_me` | Senha dos usuários demo `admin`/`aluno` |
| `ENV` | `development` | `production` esconde detalhes de erro |

Nunca commite `.env`. O `.gitignore` já bloqueia.

---

## API

Base `http://localhost:8001` (ou via proxy `http://localhost:8000`)

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| `GET` | `/api/health` | não | `{"ok": true, "dsn": "password=***"}` |
| `POST` | `/api/login` | não | `{login, senha} → {token, login, perfil}` |
| `GET` | `/api/perfil` | Bearer | retorna login/perfil |
| `GET` | `/api/mina` | Bearer | FeatureCollection ponto Sossego |
| `GET` | `/api/buffers` | Bearer | 3 Features 1/5/10km |
| `GET` | `/api/desmate?ano=&classe=&buffer=&limite=` | Bearer | GeoJSON filtrado |
| `GET` | `/api/serie` | Bearer | `[{raio_km, ano, classe, n, ha}]` (vw_serie_buffer) |
| `GET` | `/api/resumo` | Bearer | `{mina, por_ano, por_classe, buffers_ha}` |
| `POST` | `/api/desmate` | professor | `{ano, classe, lon, lat, raio_m} → {id}` |

Validação: `classe ∈ {mineracao,pastagem,outros}` · `buffer ∈ {1,5,10}` · `limite 1–5000` · coords dentro do Brasil.

---

## Testes

```bash
python testes.py          # requer servidor.py rodando
# ou com senha custom:
DEMO_PASS=dev_only_change_me python testes.py
```

```
PASSOU T0 sem token devolve 401
PASSOU T2 login ok 200 + token
...
RESULTADO: 19 / 19 testes passaram
```

Inclui: auth 401/403, filtros inválidos 400, limite, `buffer=1` interseção, e `T16b` (aluno não pode POST).

---

## Dados

* **Mina:** `-50.0790, -6.4325` (cava Sequeirinho/Sossego, Vale — ponto ajustável no QGIS)
* **Buffers:** 1 km impacto direto · 5 km funcional (vila + vicinais) · 10 km controle regional
* **Período:** 2008 (pré-expansão) · 2015 (operação plena) · 2023 (recente) — MapBiomas permite série anual, PRODES só incremento
* **Classes:** `mineracao (30) | pastagem (15) | outros` — legenda MapBiomas simplificada
* **Seed sintético:** `gerar_base.py` gera patches reprodutíveis (pastagem/outros) + área única recortada de mineração 100% dentro do 1 km

Para trocar pelo dado real, siga [`.md/ROTEIRO_QGIS.md`](.md/ROTEIRO_QGIS.md) (QGIS → `shp2pgsql` → `desmate`).

---

## Segurança

* `.env` nunca vai para o git (`.gitignore`)
* `backend/config.py` é o único que lê env; `mask_dsn()` esconde senha nos logs
* Tokens voláteis em memória + expiração 8h; hash encapsulado em `auth.sha()` (trocar por bcrypt)
* CORS restrito a `localhost:8000`; headers `nosniff`, `DENY`, `CSP default-src 'none'`
* Credenciais no repo são **demo descartáveis** (`dev_only_change_me`) — VM local, não produção

> Publicando fork? Troque `DB_PASS`/`DEMO_PASS`, regenere `gerar_base.py` e não reuse a senha demo.

---

## Licença

MIT — use para estudo, cite a fonte MapBiomas quando usar dado real.

---

<p align="center">
  <sub>Feito para disciplina de Geoprocessamento · PostGIS 31982 · Canaã dos Carajás, PA</sub>
</p>
