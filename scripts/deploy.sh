#!/bin/bash
# Deploy incremental para la VM de produccion.
# Ejecutado por: startup.sh en el primer boot, o por CI via SSH (IAP).
# Hace pull, instala deps, migra, compila frontend y reinicia los servicios systemd.
#
# Variables de entorno soportadas:
#   DEPLOY_REF - Branch/tag/commit a desplegar (default: main)
set -uo pipefail

LOGFILE="/tmp/deploy-$(date +%Y%m%d-%H%M%S).log"
REF="${DEPLOY_REF:-${1:-main}}"

exec > >(tee -a "$LOGFILE") 2>&1

echo "=== Deploy iniciado: $(date) ==="
echo "=== Log file: $LOGFILE ==="

cd /home/colegios/app

if [ ! -f .env ]; then
  echo "ERROR: falta /home/colegios/app/.env (lo crea startup.sh en el primer boot)"
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
ROLLBACK_IN_PROGRESS=0
rollback() {
  if [ $ROLLBACK_IN_PROGRESS -eq 1 ]; then
    echo "=== FATAL: Rollback recursive, abortando ==="
    exit 1
  fi
  ROLLBACK_IN_PROGRESS=1
  echo ""
  echo "=== ROLLBACK: revirtiendo a ${PREVIOUS_COMMIT} ==="
  cd /home/colegios/app
  git checkout "${PREVIOUS_COMMIT}" || { echo "ERROR: no se pudo checkout ${PREVIOUS_COMMIT}"; exit 1; }
  source .venv/bin/activate
  pip install -e . 2>&1 | tail -3
  cd frontend
  npm install 2>&1 | tail -3
  NODE_OPTIONS=--max-old-space-size=512 npm run build 2>&1 | tail -5
  cd /home/colegios/app
  sudo systemctl restart colegios-backend colegios-frontend
  echo "=== Rollback completado: ${PREVIOUS_COMMIT} ==="
  exit 1
}

trap rollback ERR

# ──────────────────────────────────────────────
# Deploy
# ──────────────────────────────────────────────
echo "=== Actualizando codigo a ${REF} ==="
git fetch origin
git checkout "${REF}"
git pull origin "${REF}" || { echo "ERROR: git pull falló"; exit 1; }

echo "=== Recargando entorno ==="
set -a
# shellcheck disable=SC1091
source .env
set +a
echo "ENVIRONMENT=${ENVIRONMENT:-not set}"

echo "=== Backend: deps ==="
source .venv/bin/activate
pip install -e . 2>&1 | tail -10

echo "=== Migraciones ==="
python -m alembic upgrade head || { echo "ERROR: migracion falló"; exit 1; }

echo "=== Frontend: build ==="
cd /home/colegios/app/frontend
if [ -f .env.production ]; then
  cp .env.production .env
  echo "Usando .env.production"
else
  echo "PUBLIC_API_BASE_URL=/api/v1" > .env
  echo "Usando .env generado"
fi
cat .env
npm install 2>&1 | tail -5
NODE_OPTIONS=--max-old-space-size=512 npm run build 2>&1 | tail -20

echo "=== Reiniciando servicios ==="
sudo systemctl restart colegios-backend
sudo systemctl restart colegios-frontend
sleep 3

# ──────────────────────────────────────────────
# Health check post-deploy
# ──────────────────────────────────────────────
echo "=== Verificando servicios ==="
for svc in colegios-backend colegios-frontend; do
  if ! sudo systemctl is-active --quiet "$svc"; then
    echo "ERROR: $svc no está corriendo"
    sudo journalctl -u "$svc" --no-pager -n 20 >&2
    exit 1
  fi
  echo "$svc: OK"
done

echo "=== Verificando API health ==="
curl -fsS --retry 5 --retry-delay 3 --retry-all-errors http://127.0.0.1:8000/api/v1/health || {
  echo "ERROR: API health check falló"
  sudo journalctl -u colegios-backend --no-pager -n 50 >&2
  exit 1
}
echo "API health: OK"

# Desactivar rollback trap — deploy exitoso
trap - ERR

echo ""
echo "=== Deploy OK: $(date) ==="
