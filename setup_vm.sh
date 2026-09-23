#!/bin/bash
# Setup VM Ubuntu Server - Sossego Desmatamento (PostGIS 31982)
# Uso: chmod +x setup_vm.sh && ./setup_vm.sh
# Vars via env: DB_USER, DB_PASS, DB_NAME (defaults dev descartável)
set -e

DB_USER="${DB_USER:-ubunto}"
DB_PASS="${DB_PASS:-dev_only_change_me}"
DB_NAME="${DB_NAME:-sossego_desmate}"

echo "=== Setup VM Sossego (DB $DB_NAME / $DB_USER) ==="

# 1. PostgreSQL + PostGIS
sudo apt update
sudo apt install -y postgresql postgresql-contrib postgis postgresql-16-postgis-3

# 2. Iniciar serviço
sudo systemctl enable postgresql
sudo systemctl start postgresql

# 3. Criar usuário e banco
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS' CREATEDB CREATEROLE;" || echo "user $DB_USER já existe"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" || echo "db já existe"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# 4. Habilitar PostGIS no banco
sudo -u postgres psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS postgis; SELECT postgis_version();"

# 5. Configurar acesso (host)
PG_CONF=$(sudo -u postgres psql -t -c "SHOW config_file;" | xargs dirname)/../main/postgresql.conf
HBA_CONF=$(sudo -u postgres psql -t -c "SHOW hba_file;" | tr -d ' ')
echo "Config: $PG_CONF"
echo "HBA: $HBA_CONF"

sudo sed -i "s/^#*listen_addresses.*/listen_addresses = '*'/ " /etc/postgresql/16/main/postgresql.conf || true
if ! sudo grep -q "host.*all.*all.*0.0.0.0/0" "$HBA_CONF"; then
  echo "host all all 0.0.0.0/0 md5" | sudo tee -a "$HBA_CONF"
fi
sudo systemctl restart postgresql

# 6. Aplicar schema
if [ -f schema.sql ]; then
  PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -f schema.sql
  echo "schema.sql aplicado"
else
  echo "schema.sql não encontrado no diretório atual"
fi

# 7. Gerar base sintética (opcional)
if [ -f gerar_base.py ]; then
  echo "Gerando base sintética..."
  python3 -m venv .venv 2>/dev/null || true
  # shellcheck disable=SC1091
  source .venv/bin/activate 2>/dev/null || true
  pip install -q "psycopg[binary]" || pip3 install -q "psycopg[binary]"
  python3 gerar_base.py || echo "gerar_base.py falhou - rode manualmente: python3 gerar_base.py"
fi

# 8. Info NAT VirtualBox (configurar no host: NAT 15432->5432, 2222->22)
echo ""
echo "=== Setup concluído ==="
echo "Banco: $DB_NAME | user: $DB_USER | host VM: localhost:5432 | host externo: localhost:15432"
echo "Teste: PGPASSWORD=\"\$DB_PASS\" psql -h localhost -U $DB_USER -d $DB_NAME -c 'SELECT postgis_version();'"
echo "Carga: python3 gerar_base.py"
echo "Servidor: python3 servidor.py -> http://localhost:8000/login.html"
echo "  Demo logins: admin/aluno (senha via DEMO_PASS, default dev_only_change_me)"
echo "Testes: python3 testes.py"
