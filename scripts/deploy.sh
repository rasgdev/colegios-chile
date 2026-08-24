#!/bin/bash
# Deploy incremental para la VM de produccion.
# Ejecutado por: startup.sh en el primer boot, o por CI via SSH (IAP).
# Hace pull, instala deps, migra, compila frontend y reinicia los servicios systemd.
#
# Variables de entorno soportadas:
#   DEPLOY_REF - Branch/tag/commit a desplegar (default: main)
set -euo pipefail

REF="${DEPLOY_REF:-${1:-main}}"

cd /home/colegios/app

if [ ! -f .env ]; then
  echo "ERROR: falta /home/colegios/app/.env (lo crea startup.sh en el primer boot)" >&2
  exit 1
fi

# ──────────────────────────────────────────────
# Guardar commit actual para rollback
# ──────────────────────────────────────────────
PREVIOUS_COMMIT=$(git rev-parse HEAD)
echo "=== Commit actual: ${PREVIOUS_COMMIT} ==="

# ──────────────────────────────────────────────
# Rollback: revertir código + reinstalar deps + reconstruir frontend + reiniciar
# Nota: NO revierte migraciones de DB (alembic downgrade es destructivo)
# ──────────────────────────────────────────────
rollback() {
  echo "=== ROLLBACK: revirtiendo a ${PREVIOUS_COMMIT} ===" >&2
  cd /home/colegios/app
  git checkout "${PREVIOUS_COMMIT}" || { echo "ERROR: no se pudo checkout ${PREVIOUS_COMMIT}" >&2; exit 1; }
  source .venv/bin/activate
  pip install -e . 2>&1 | tail -3
  cd frontend
  npm install 2>&1 | tail -3
  NODE_OPTIONS=--max-old-space-size=512 npm run build 2>&1 | tail -5
  cd /home/colegios/app
  sudo systemctl restart colegios-backend colegios-frontend
  echo "=== Rollback completado: ${PREVIOUS_COMMIT} ===" >&2
  exit 1
}

trap rollback ERR

# ──────────────────────────────────────────────
# Deploy
# ──────────────────────────────────────────────
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
if [ -f .env.production ]; then
  cp .env.production .env
else
  echo "PUBLIC_API_BASE_URL=/api/v1" > .env
fi
npm install
NODE_OPTIONS=--max-old-space-size=512 npm run build

echo "=== Reiniciando servicios ==="
sudo systemctl restart colegios-backend
sudo systemctl restart colegios-frontend

# ──────────────────────────────────────────────
# Health check post-deploy
# ──────────────────────────────────────────────
echo "=== Verificando servicios ==="
for svc in colegios-backend colegios-frontend; do
  if ! sudo systemctl is-active --quiet "$svc"; then
    echo "ERROR: $svc no está corriendo" >&2
    sudo journalctl -u "$svc" --no-pager -n 20 >&2
    exit 1
  fi
done

echo "=== Verificando API health ==="
if ! curl -fsS --retry 5 --retry-delay 3 --retry-all-errors http://127.0.0.1:8000/api/v1/health; then
  echo "ERROR: API health check falló" >&2
  exit 1
fi

# Desactivar rollback trap — deploy exitoso
trap - ERR

echo "=== Deploy OK ==="
