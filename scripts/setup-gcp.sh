#!/bin/bash
# setup-gcp.sh — Setup automatizado para GCP e2-micro
# Ejecutar en la VM despues de crearla con gcloud
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
log() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo "=== Colegios Chile — Setup GCP e2-micro ==="
echo ""

# --- 1. Actualizar sistema ---
echo "1/10 Actualizando sistema..."
sudo apt update -qq && sudo apt upgrade -y -qq
log "Sistema actualizado"

# --- 2. Crear usuario ---
echo "2/10 Creando usuario 'colegios'..."
if ! id "colegios" &>/dev/null; then
    sudo adduser --system --group --home /var/www/colegios-chile colegios
    log "Usuario creado"
else
    log "Usuario ya existe"
fi

# --- 3. Instalar PostgreSQL 15 ---
echo "3/10 Instalando PostgreSQL 15..."
if ! command -v psql &>/dev/null; then
    sudo apt install -y -qq postgresql postgresql-contrib
    log "PostgreSQL instalado"
else
    log "PostgreSQL ya instalado"
fi

# --- 4. Instalar Python 3.12 ---
echo "4/10 Instalando Python 3.12..."
if ! command -v python3 &>/dev/null; then
    sudo apt install -y -qq python3 python3-pip python3-venv
    log "Python instalado"
else
    log "Python ya instalado"
fi

# --- 5. Instalar Node.js 20 ---
echo "5/10 Instalando Node.js 20..."
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y -qq nodejs
    log "Node.js instalado"
else
    log "Node.js ya instalado"
fi

# --- 6. Instalar Nginx ---
echo "6/10 Instalando Nginx..."
if ! command -v nginx &>/dev/null; then
    sudo apt install -y -qq nginx
    log "Nginx instalado"
else
    log "Nginx ya instalado"
fi

# --- 7. Instalar Certbot ---
echo "7/10 Instalando Certbot..."
if ! command -v certbot &>/dev/null; then
    sudo apt install -y -qq certbot python3-certbot-nginx
    log "Certbot instalado"
else
    log "Certbot ya instalado"
fi

# --- 8. Configurar PostgreSQL (tuning minimo RAM) ---
echo "8/10 Configurando PostgreSQL..."

PG_CONF="/etc/postgresql/15/main/postgresql.conf"
if [ -f "$PG_CONF" ]; then
    sudo sed -i "s/^#*shared_buffers =.*/shared_buffers = 64MB/" "$PG_CONF"
    sudo sed -i "s/^#*effective_cache_size =.*/effective_cache_size = 128MB/" "$PG_CONF"
    sudo sed -i "s/^#*work_mem =.*/work_mem = 4MB/" "$PG_CONF"
    sudo sed -i "s/^#*maintenance_work_mem =.*/maintenance_work_mem = 32MB/" "$PG_CONF"
    sudo sed -i "s/^#*max_connections =.*/max_connections = 20/" "$PG_CONF"
    sudo sed -i "s/^#*wal_buffers =.*/wal_buffers = 4MB/" "$PG_CONF"
    sudo sed -i "s/^#*listen_addresses =.*/listen_addresses = 'localhost'/" "$PG_CONF"
    sudo systemctl restart postgresql
    log "PostgreSQL tuneado (64MB shared_buffers, 20 max_connections)"
else
    warn "PostgreSQL no encontrado en $PG_CONF"
fi

# --- 9. Crear rol y base de datos ---
echo "9/10 Configurando base de datos..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='colegios'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE ROLE colegios WITH LOGIN PASSWORD 'colegios';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='colegios'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE colegios OWNER colegios;"
log "Base de datos 'colegios' lista"

# --- 10. Verificar versiones ---
echo "10/10 Verificando instalacion..."
echo ""
echo "  Node.js:  $(node --version)"
echo "  Python:   $(python3 --version)"
echo "  PostgreSQL: $(psql --version)"
echo "  Nginx:    $(nginx -v 2>&1)"
echo ""
log "Setup completado!"
echo ""
echo "Siguientes pasos:"
echo "  1. Clonar el repo:  cd /var/www && git clone <repo-url> colegios-chile"
echo "  2. Instalar deps:   cd colegios-chile && pip install -r requirements-prod.txt"
echo "  3. Compilar frontend: cd frontend && npm install && npm run build"
echo "  4. Cargar DB:       make init-db migrate load-db"
echo "  5. Configurar Nginx: copiar scripts/nginx-gcp.conf a /etc/nginx/sites-available/"
echo "  6. Activar systemd:  systemctl start colegios-api colegios-web"
echo "  7. SSL:             certbot --nginx -d TU_DOMINIO"
