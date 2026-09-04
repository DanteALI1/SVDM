#!/usr/bin/env bash
# SVDB full installer for Red OS (empty server).
# Installs PostgreSQL, Redis, Nginx, Python, Node, deploys app, bootstraps,
# prints ALL credentials and saves them to /root/svdb-credentials.txt
set -euo pipefail

SVDB_ROOT="${SVDB_ROOT:-/opt/svdb}"
SVDB_USER="${SVDB_USER:-svdb}"
CRED_FILE="${CRED_FILE:-/root/svdb-credentials.txt}"
DOMAIN="${SVDB_DOMAIN:-$(hostname -f 2>/dev/null || hostname)}"
APP_URL="${SVDB_URL:-http://${DOMAIN}}"

log() { echo "[SVDB] $*"; }

if [[ $EUID -ne 0 ]]; then
  echo "Run as root"; exit 1
fi

log "Installing system packages (Red OS / RHEL-compatible)..."
if command -v dnf >/dev/null 2>&1; then
  PKG=dnf
elif command -v yum >/dev/null 2>&1; then
  PKG=yum
else
  echo "Neither dnf nor yum found"; exit 1
fi

$PKG -y install \
  postgresql postgresql-server postgresql-contrib \
  redis nginx python3 python3-pip python3-devel \
  gcc gcc-c++ make libpq-devel git curl tar \
  || true

# Node.js 20 via NodeSource or system module if available
if ! command -v node >/dev/null 2>&1; then
  log "Installing Node.js..."
  curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - || true
  $PKG -y install nodejs || true
fi


# Init PostgreSQL if needed
if [[ ! -d /var/lib/pgsql/data/base ]] && [[ ! -f /var/lib/pgsql/data/PG_VERSION ]]; then
  log "Initializing PostgreSQL..."
  postgresql-setup --initdb 2>/dev/null || postgresql-setup initdb 2>/dev/null || \
    su - postgres -c "initdb -D /var/lib/pgsql/data" || true
fi

systemctl enable --now postgresql || systemctl enable --now postgresql-16 || true
systemctl enable --now redis || systemctl enable --now redis-server || true
systemctl enable --now nginx || true

DB_NAME="svdb"
DB_USER="svdb"
DB_PASS="$(openssl rand -base64 18 | tr -d '/+=' | head -c 20)"
DJANGO_SECRET="$(openssl rand -hex 32)"
PLATFORM_USER="platform"
PLATFORM_PASS="$(openssl rand -base64 12 | tr -d '/+=' | head -c 16)Aa1!"
TENANT_USER="admin"
TENANT_PASS="$(openssl rand -base64 12 | tr -d '/+=' | head -c 16)Aa1!"

log "Creating database and user..."
su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'\"" | grep -q 1 || \
  su - postgres -c "psql -c \"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';\""
su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'\"" | grep -q 1 || \
  su - postgres -c "psql -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};\""
su - postgres -c "psql -c \"ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';\""
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};\""

# Ensure md5/scram auth for local connections
PG_HBA=$(find /var/lib/pgsql /etc/postgresql -name pg_hba.conf 2>/dev/null | head -1 || true)
if [[ -n "${PG_HBA}" ]]; then
  if ! grep -q "svdb" "$PG_HBA"; then
    sed -i '1i# SVDB\nlocal   all             svdb                                    scram-sha-256\nhost    all             svdb            127.0.0.1/32            scram-sha-256\nhost    all             svdb            ::1/128                 scram-sha-256' "$PG_HBA" || true
    systemctl reload postgresql || systemctl reload postgresql-16 || true
  fi
fi

id "$SVDB_USER" >/dev/null 2>&1 || useradd --system --home "$SVDB_ROOT" --shell /sbin/nologin "$SVDB_USER"
mkdir -p "$SVDB_ROOT" /var/lib/svdb/media /var/log/svdb

# Resolve application source. Prefer SVDB_SRC; otherwise expect this script at
# <repo>/deploy/redos/install-svdb.sh (full git clone), never a lone downloaded copy.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${SVDB_SRC:-}" ]]; then
  REPO_ROOT="$(cd "${SVDB_SRC}" && pwd)"
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

is_svdb_repo() {
  local root="$1"
  [[ -f "$root/backend/manage.py" ]] \
    && [[ -f "$root/frontend/package.json" ]] \
    && [[ -f "$root/backend/requirements.txt" ]]
}

if [[ "$REPO_ROOT" == "/" ]] || [[ "$REPO_ROOT" == "/opt" ]] || [[ "$REPO_ROOT" == "/root" ]] || [[ "$REPO_ROOT" == "/tmp" ]]; then
  echo "ERROR: Refusing to deploy from '${REPO_ROOT}' (unsafe source)."
  echo "Clone the full SVDB repo first, then run the installer from inside it:"
  echo "  cd /opt && git clone https://github.com/DanteALI1/SVDM.git svdb-src"
  echo "  cd /opt/svdb-src && bash deploy/redos/install-svdb.sh"
  echo "Or set SVDB_SRC=/path/to/full/svdb/repo"
  exit 1
fi

if ! is_svdb_repo "$REPO_ROOT"; then
  echo "ERROR: '${REPO_ROOT}' is not a full SVDB checkout (missing backend/frontend)."
  echo "Do not run a standalone copy of install-svdb.sh. Clone the repository first."
  exit 1
fi

if [[ "$REPO_ROOT" -ef "$SVDB_ROOT" ]]; then
  log "Application already at ${SVDB_ROOT}; skipping copy."
else
  log "Deploying application from ${REPO_ROOT} -> ${SVDB_ROOT}..."
  RSYNC_EXCLUDES=(
    --exclude .git
    --exclude node_modules
    --exclude .next
    --exclude __pycache__
    --exclude /venv
    --exclude /.env
  )
  # If destination lives under the source tree, skip it (prevents recursive nesting).
  if [[ "$SVDB_ROOT" == "$REPO_ROOT"/* ]]; then
    RSYNC_EXCLUDES+=(--exclude "/${SVDB_ROOT#"$REPO_ROOT"/}")
  fi
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$REPO_ROOT/" "$SVDB_ROOT/"
  else
    # Prefer explicit trees over "cp -a src/." which can recurse into SVDB_ROOT.
    rm -rf "$SVDB_ROOT/backend" "$SVDB_ROOT/frontend" "$SVDB_ROOT/deploy" "$SVDB_ROOT/docs"
    cp -a "$REPO_ROOT/backend" "$REPO_ROOT/frontend" "$SVDB_ROOT/"
    [[ -d "$REPO_ROOT/deploy" ]] && cp -a "$REPO_ROOT/deploy" "$SVDB_ROOT/"
    [[ -d "$REPO_ROOT/docs" ]] && cp -a "$REPO_ROOT/docs" "$SVDB_ROOT/"
    for f in docker-compose.yml .env.example README.md; do
      [[ -f "$REPO_ROOT/$f" ]] && cp -a "$REPO_ROOT/$f" "$SVDB_ROOT/"
    done
  fi
fi

if ! is_svdb_repo "$SVDB_ROOT"; then
  echo "ERROR: deploy to ${SVDB_ROOT} incomplete; aborting before venv/bootstrap."
  exit 1
fi

cat > "$SVDB_ROOT/.env" <<EOF
DEBUG=false
DJANGO_SECRET_KEY=${DJANGO_SECRET}
ALLOWED_HOSTS=*
CORS_ALLOWED_ORIGINS=${APP_URL}
CSRF_TRUSTED_ORIGINS=${APP_URL}
POSTGRES_DB=${DB_NAME}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
DATABASE_URL=postgres://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}
REDIS_URL=redis://127.0.0.1:6379/0
SVDB_PLATFORM_USER=${PLATFORM_USER}
SVDB_PLATFORM_PASSWORD=${PLATFORM_PASS}
SVDB_TENANT_NAME=Default
SVDB_TENANT_SLUG=default
SVDB_TENANT_USER=${TENANT_USER}
SVDB_TENANT_PASSWORD=${TENANT_PASS}
SESSION_IDLE_MINUTES=60
AUDIT_RETENTION_DAYS=180
EOF

log "Python venv + backend deps..."
python3 -m venv "$SVDB_ROOT/venv"
# shellcheck disable=SC1091
source "$SVDB_ROOT/venv/bin/activate"
pip install --upgrade pip
pip install -r "$SVDB_ROOT/backend/requirements.txt"
pip install gunicorn

cd "$SVDB_ROOT/backend"
export $(grep -v '^#' "$SVDB_ROOT/.env" | xargs)
python manage.py migrate --noinput
python manage.py collectstatic --noinput || true
python manage.py bootstrap_svdb \
  --platform-user "$PLATFORM_USER" \
  --platform-password "$PLATFORM_PASS" \
  --tenant-user "$TENANT_USER" \
  --tenant-password "$TENANT_PASS"

log "Building frontend..."
cd "$SVDB_ROOT/frontend"
npm install
API_URL=http://127.0.0.1:8000 npm run build

chown -R "$SVDB_USER:$SVDB_USER" "$SVDB_ROOT" /var/lib/svdb /var/log/svdb

log "Creating systemd units..."
cat > /etc/systemd/system/svdb-backend.service <<EOF
[Unit]
Description=SVDB Backend (Gunicorn)
After=network.target postgresql.service redis.service

[Service]
User=${SVDB_USER}
Group=${SVDB_USER}
WorkingDirectory=${SVDB_ROOT}/backend
EnvironmentFile=${SVDB_ROOT}/.env
ExecStart=${SVDB_ROOT}/venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/svdb-worker.service <<EOF
[Unit]
Description=SVDB Celery Worker
After=network.target redis.service svdb-backend.service

[Service]
User=${SVDB_USER}
Group=${SVDB_USER}
WorkingDirectory=${SVDB_ROOT}/backend
EnvironmentFile=${SVDB_ROOT}/.env
ExecStart=${SVDB_ROOT}/venv/bin/celery -A config worker -l info
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/svdb-beat.service <<EOF
[Unit]
Description=SVDB Celery Beat
After=network.target redis.service svdb-backend.service

[Service]
User=${SVDB_USER}
Group=${SVDB_USER}
WorkingDirectory=${SVDB_ROOT}/backend
EnvironmentFile=${SVDB_ROOT}/.env
ExecStart=${SVDB_ROOT}/venv/bin/celery -A config beat -l info
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/svdb-frontend.service <<EOF
[Unit]
Description=SVDB Frontend (Next.js)
After=network.target svdb-backend.service

[Service]
User=${SVDB_USER}
Group=${SVDB_USER}
WorkingDirectory=${SVDB_ROOT}/frontend
Environment=NODE_ENV=production
Environment=API_URL=http://127.0.0.1:8000
ExecStart=/usr/bin/npm run start -- -H 127.0.0.1 -p 3000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/nginx/conf.d/svdb.conf <<EOF
server {
    listen 80 default_server;
    server_name ${DOMAIN};

    client_max_body_size 50m;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /media/ {
        alias /var/lib/svdb/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOF

systemctl daemon-reload
systemctl enable --now svdb-backend svdb-worker svdb-beat svdb-frontend
systemctl reload nginx || systemctl restart nginx

umask 077
cat > "$CRED_FILE" <<EOF
SVDB installation credentials
=============================
URL:                 ${APP_URL}
API:                 ${APP_URL}/api/
OpenAPI docs:        ${APP_URL}/api/docs/

Database host:       127.0.0.1
Database port:       5432
Database name:       ${DB_NAME}
Database user:       ${DB_USER}
Database password:   ${DB_PASS}

Django secret key:   ${DJANGO_SECRET}

Platform admin:      ${PLATFORM_USER}
Platform password:   ${PLATFORM_PASS}

Tenant:              Default (slug=default)
Tenant admin:        ${TENANT_USER}
Tenant password:     ${TENANT_PASS}

Install path:        ${SVDB_ROOT}
Credentials file:    ${CRED_FILE}
EOF
chmod 600 "$CRED_FILE"

echo
echo "============================================================"
echo " SVDB installation complete"
echo "============================================================"
cat "$CRED_FILE"
echo "============================================================"
echo " Credentials also saved to ${CRED_FILE}"
echo "============================================================"
