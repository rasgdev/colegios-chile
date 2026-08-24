#!/bin/bash
# Startup script robusto para la VM colegios-server (e2-micro, 1GB RAM).
# Ejecutado por GCE en cada boot. Debe ser idempotente y tolerante a fallos.
#
# Variables inyectadas por terraform templatefile:
#   ${repo_url}    - URL del repo Git
#   ${repo_branch} - Branch a desplegar
#   ${db_password} - Password de PostgreSQL

export DEBIAN_FRONTEND=noninteractive
LOG="/var/log/startup.log"

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

# Loguea y ejecuta un paso. Reintenta hasta $1 veces con $2s entre intentos.
# Uso: run_with_retries 3 15 "descripcion" comando args...
run_with_retries() {
  local max_attempts=$1
  local delay=$2
  shift 2
  local desc="$1"
  shift
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    log "  Intento $attempt/$max_attempts: $desc"
    if "$@" >>"$LOG" 2>&1; then
      log "  OK: $desc"
      return 0
    fi
    log "  FALLO intento $attempt de $desc"
    attempt=$((attempt + 1))
    [ $attempt -le $max_attempts ] && sleep "$delay"
  done
  log "  ERROR tras $max_attempts intentos: $desc"
  return 1
}

log() {
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$ts] $*" | tee -a "$LOG"
}

# ──────────────────────────────────────────────
# 0. Cleanup de intentos previos fallidos
# ──────────────────────────────────────────────
log "=== Limpiando estado de intentos previos ==="
rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock* 2>/dev/null || true
dpkg --configure -a 2>/dev/null || true
killall -9 apt apt-get dpkg 2>/dev/null || true
log "  Limpieza completada"

# ──────────────────────────────────────────────
# 1. Swap (buffer para e2-micro con 1GB RAM)
# ──────────────────────────────────────────────
if [ ! -f /swapfile ]; then
  log "=== Creando swap 512MB ==="
  fallocate -l 512M /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=512
  chmod 600 /swapfile
  mkswap /swapfile >>"$LOG" 2>&1
  swapon /swapfile >>"$LOG" 2>&1
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  log "  Swap activado"
else
  log "=== Swap ya existe, omitiendo ==="
fi

# ──────────────────────────────────────────────
# 2. Sistema base (apt update + upgrade + deps)
# ──────────────────────────────────────────────
log "=== Actualizando sistema ==="
run_with_retries 3 15 "apt-get update" apt-get update || { log "ERROR critico: apt-get update fallo tras 3 intentos"; exit 1; }
run_with_retries 2 30 "apt-get upgrade" apt-get upgrade -y || log "WARN: apt-get upgrade fallo (continuando)"

log "=== Instalando dependencias base ==="
run_with_retries 3 15 "apt-get install deps" apt-get install -y \
  postgresql postgresql-contrib \
  python3 python3-pip python3-venv \
  nginx git curl || { log "ERROR critico: install deps fallo"; exit 1; }

# ──────────────────────────────────────────────
# 3. Node.js 20 LTS
# ──────────────────────────────────────────────
log "=== Instalando Node.js 22 LTS ==="
if ! command -v node &>/dev/null || ! node -v | grep -q '^v22'; then
  run_with_retries 3 15 "nodesource setup" curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  run_with_retries 2 15 "apt-get install nodejs" apt-get install -y nodejs || { log "ERROR critico: nodejs install fallo"; exit 1; }
  log "  Node.js $(node -v) instalado"
else
  log "  Node.js $(node -v) ya presente, omitiendo"
fi

# ──────────────────────────────────────────────
# 4. PostgreSQL tuning (e2-micro / 1GB RAM)
# ──────────────────────────────────────────────
log "=== Configurando PostgreSQL ==="
mkdir -p /etc/postgresql/15/main/postgresql.conf.d
cat > /etc/postgresql/15/main/postgresql.conf.d/tuning.conf << 'PGCONF'
# Memoria
shared_buffers = 64MB
effective_cache_size = 128MB
work_mem = 4MB
maintenance_work_mem = 32MB

# Conexiones
max_connections = 20

# WAL
wal_buffers = 4MB
checkpoint_completion_target = 0.9

# Logging (minimo)
logging_collector = off
log_min_messages = warning

# Seguridad
listen_addresses = 'localhost'
PGCONF

grep -q "tuning.conf" /etc/postgresql/15/main/postgresql.conf 2>/dev/null || \
  echo "include 'postgresql.conf.d/tuning.conf'" >> /etc/postgresql/15/main/postgresql.conf

systemctl restart postgresql
log "  PostgreSQL reiniciado"

# ──────────────────────────────────────────────
# 5. Crear base de datos y usuario
# ──────────────────────────────────────────────
log "=== Creando base de datos y usuario ==="
sudo -u postgres psql -c "CREATE USER colegios WITH PASSWORD '${db_password}';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE colegios OWNER colegios;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE colegios TO colegios;" 2>/dev/null || true
log "  DB y usuario configurados (idempotente)"

# ──────────────────────────────────────────────
# 6. Usuario de deploy
# ──────────────────────────────────────────────
log "=== Configurando usuario de deploy ==="
id -u colegios >/dev/null 2>&1 || useradd -m -s /bin/bash colegios

cat > /etc/sudoers.d/colegios << 'SUDOEOF'
colegios ALL=(root) NOPASSWD: /usr/bin/systemctl restart colegios-backend colegios-frontend, /usr/bin/systemctl status colegios-backend colegios-frontend
SUDOEOF
chmod 440 /etc/sudoers.d/colegios
log "  Usuario colegios configurado"

# ──────────────────────────────────────────────
# 7. Clonar o actualizar repositorio
# ──────────────────────────────────────────────
log "=== Clonando/actualizando repositorio ==="
mkdir -p /home/colegios
if [ -d /home/colegios/app/.git ]; then
  cd /home/colegios/app && git fetch origin >>"$LOG" 2>&1 && \
    git checkout "${repo_branch}" >>"$LOG" 2>&1 && \
    git pull origin "${repo_branch}" >>"$LOG" 2>&1
  log "  Repo actualizado a ${repo_branch}"
else
  rm -rf /home/colegios/app 2>/dev/null || true
  run_with_retries 3 10 "git clone" git clone -b "${repo_branch}" "${repo_url}" /home/colegios/app || { log "ERROR critico: git clone fallo"; exit 1; }
  log "  Repo clonado a ${repo_branch}"
fi

# ──────────────────────────────────────────────
# 8. Backend venv y .env
# ──────────────────────────────────────────────
log "=== Configurando backend ==="
cd /home/colegios/app
[ -d .venv ] || python3 -m venv .venv

if [ -f .env.production ]; then
  sed "s/\${DB_PASSWORD}/${db_password}/g" .env.production > .env
  log "  .env configurado desde .env.production"
else
  cat > .env << ENVEOF
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://colegios:${db_password}@localhost:5432/colegios
API_PORT=8000
FRONTEND_PORT=4321
LOG_LEVEL=WARNING
ENVEOF
  log "  .env configurado inline (fallback)"
fi

# ──────────────────────────────────────────────
# 9. Servicios systemd
# ──────────────────────────────────────────────
log "=== Configurando servicios systemd ==="
cat > /etc/systemd/system/colegios-backend.service << 'SVCEOF'
[Unit]
Description=Colegios Chile Backend (FastAPI)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/colegios/app
Environment=PATH=/home/colegios/app/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/colegios/app/.venv/bin/uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

cat > /etc/systemd/system/colegios-frontend.service << 'SVCEOF'
[Unit]
Description=Colegios Chile Frontend (Astro SSR)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/colegios/app/frontend
Environment=PATH=/home/colegios/app/frontend/node_modules/.bin:/usr/local/bin:/usr/bin:/bin
Environment=HOST=127.0.0.1
Environment=PORT=4321
Environment=NODE_ENV=production
Environment=INTERNAL_API_BASE_URL=http://127.0.0.1:8000/api/v1
ExecStart=/usr/bin/node ./dist/server/entry.mjs
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable colegios-backend colegios-frontend
log "  Servicios systemd configurados y habilitados"

# ──────────────────────────────────────────────
# 10. Nginx
# ──────────────────────────────────────────────
log "=== Configurando Nginx ==="
cat > /etc/nginx/sites-available/colegios << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:4321;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/colegios /etc/nginx/sites-enabled/colegios
rm -f /etc/nginx/sites-enabled/default
nginx -t >>"$LOG" 2>&1 && systemctl reload nginx
log "  Nginx configurado"

# ──────────────────────────────────────────────
# 11. Deploy inicial (best-effort)
# ──────────────────────────────────────────────
log "=== Deploy inicial ==="
bash /home/colegios/app/scripts/deploy.sh "${repo_branch}" >>"$LOG" 2>&1 || \
  log "WARN: deploy inicial fallo; se reintentara via CI/CD"

# ──────────────────────────────────────────────
# 12. Permisos y sentinel
# ──────────────────────────────────────────────
chown -R colegios:colegios /home/colegios
touch /home/colegios/.setup-complete

log "=== Setup completo ==="
log "IP: $(curl -s ifconfig.me 2>/dev/null || echo 'no disponible')"
log "Estado servicios:"
systemctl --no-pager status colegios-backend colegios-frontend nginx --no-legend | tee -a "$LOG"
