#!/bin/bash
set -e

export DEBIAN_FRONTEND=noninteractive

echo "=== Actualizando sistema ==="
apt-get update && apt-get upgrade -y

echo "=== Instalando dependencias base ==="
apt-get install -y \
  postgresql postgresql-contrib \
  python3 python3-pip python3-venv \
  nginx certbot python3-certbot-nginx \
  git curl

echo "=== Instalando Node.js 20 LTS ==="
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

echo "=== Configurando PostgreSQL (tuneo para e2-micro / 1GB RAM) ==="
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

grep -q "tuning.conf" /etc/postgresql/15/main/postgresql.conf || \
  echo "include 'postgresql.conf.d/tuning.conf'" >> /etc/postgresql/15/main/postgresql.conf

systemctl restart postgresql

echo "=== Creando base de datos y usuario ==="
sudo -u postgres psql -c "CREATE USER colegios WITH PASSWORD '${db_password}';" || true
sudo -u postgres psql -c "CREATE DATABASE colegios OWNER colegios;" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE colegios TO colegios;" || true

echo "=== Creando usuario de deploy ==="
id -u colegios >/dev/null 2>&1 || useradd -m -s /bin/bash colegios
cat > /etc/sudoers.d/colegios << 'SUDOEOF'
colegios ALL=(root) NOPASSWD: /usr/bin/systemctl restart colegios-backend colegios-frontend, /usr/bin/systemctl status colegios-backend colegios-frontend
SUDOEOF
chmod 440 /etc/sudoers.d/colegios

echo "=== Clonando repositorio ==="
mkdir -p /home/colegios
if [ -d /home/colegios/app ]; then
  cd /home/colegios/app && git fetch origin && git checkout ${repo_branch} && git pull origin ${repo_branch}
else
  git clone -b ${repo_branch} ${repo_url} /home/colegios/app
fi

echo "=== Configurando backend (venv) ==="
cd /home/colegios/app
python3 -m venv .venv

cat > .env << ENVEOF
DATABASE_URL=postgresql+asyncpg://colegios:${db_password}@localhost:5432/colegios
API_PORT=8000
FRONTEND_PORT=4321
LOG_LEVEL=INFO
ENVEOF

echo "=== Configurando servicios systemd ==="
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
ExecStart=/usr/bin/node ./dist/server/entry.mjs
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable colegios-backend
systemctl enable colegios-frontend

echo "=== Configurando Nginx ==="
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
nginx -t && systemctl reload nginx

echo "=== Deploy inicial ==="
bash /home/colegios/app/scripts/deploy.sh ${repo_branch}

chown -R colegios:colegios /home/colegios

echo "=== Setup completo ==="
echo "IP: $(curl -s ifconfig.me)"
echo "Estado servicios:"
systemctl --no-pager status colegios-backend colegios-frontend nginx --no-legend