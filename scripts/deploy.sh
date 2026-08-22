#!/bin/bash
# Deploy incremental para la VM de produccion.
# Ejecutado por: startup.sh en el primer boot, o por CI via SSH (IAP).
# Hace pull, instala deps, migra, compila frontend y reinicia los servicios systemd.
set -euo pipefail

REF="${1:-main}"

cd /home/colegios/app

if [ ! -f .env ]; then
  echo "ERROR: falta /home/colegios/app/.env (lo crea startup.sh en el primer boot)" >&2
  exit 1
fi

echo "=== Actualizando codigo a ${REF} ==="
git fetch origin
git checkout "${REF}"
git pull origin "${REF}"

echo "=== Recargando entorno ==="
set -a
# shellcheck disable=SC1091
source .env
set +a

echo "=== Backend: deps ==="
source .venv/bin/activate
pip install -e .

echo "=== Migraciones ==="
python -m alembic upgrade head

echo "=== Frontend: build ==="
cd /home/colegios/app/frontend
echo "PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1" > .env
npm install
NODE_OPTIONS=--max-old-space-size=512 npm run build

echo "=== Reiniciando servicios ==="
systemctl restart colegios-backend colegios-frontend

echo "=== Deploy OK ==="