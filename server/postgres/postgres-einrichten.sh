#!/usr/bin/env bash
# PostgreSQL + pgvector fuer den Vault-Index einrichten. Start: sudo bash ~/MA-Server/server/postgres/postgres-einrichten.sh
# Legt an: Datenbank "vault", Benutzer "vaultq" (nur lokal), Erweiterungen vector und unaccent.
# Passwort nur in /etc/ma-home/vaultq.pgpass (0640 root:andrew), nie im Vault oder in Git. SQLite/vault-q bleiben unveraendert.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Bitte mit sudo starten."; exit 1; }

apt-get update -qq
apt-get install -y postgresql postgresql-contrib python3-psycopg
VER=$(ls /usr/lib/postgresql | sort -V | tail -1)
apt-get install -y "postgresql-${VER}-pgvector" || { echo "FEHLER: postgresql-${VER}-pgvector nicht installierbar. Ausgabe an Claude melden."; exit 2; }
systemctl enable --now postgresql

install -d -m 0750 -o root -g andrew /etc/ma-home
PWFILE=/etc/ma-home/vaultq.pgpass
if [ ! -s "$PWFILE" ]; then
  ( umask 077; openssl rand -base64 24 | tr -d '/+=\n' > "$PWFILE" )
  chown root:andrew "$PWFILE"; chmod 0640 "$PWFILE"
fi
PW=$(cat "$PWFILE")

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='vaultq') THEN CREATE ROLE vaultq LOGIN PASSWORD '$PW'; END IF;
END \$\$;
SELECT 'CREATE DATABASE vault OWNER vaultq' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='vault')\gexec
SQL
sudo -u postgres psql -d vault -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;" -c "CREATE EXTENSION IF NOT EXISTS unaccent;"

echo "--- Pruefung ---"
sudo -u postgres psql -d vault -Atc "select version();" -c "select 'vector '||extversion from pg_extension where extname='vector';"
sudo -u postgres psql -Atc "show listen_addresses;"
echo "Fertig. Ergebnis (Version, vector, listen_addresses) an Claude melden."
