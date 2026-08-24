# Plan: Eliminar Rollback Automático en Deploy

**Fecha:** 2026-08-24
**Estado:** Propuesto
**Experiencia:** Basado en deploy fallido real a GCP

---

## Problema Identificado

El `trap rollback ERR` en `deploy.sh` hace revert automático al commit anterior cuando cualquier comando falla.

### Comportamiento Actual

```bash
trap rollback ERR  # Al detectar error, hace rollback automático

rollback() {
  git checkout PREVIOUS_COMMIT
  pip install -e .
  npm run build
  systemctl restart
  exit 1
}
```

### Issues

| # | Issue | Impacto |
|---|-------|---------|
| 1 | Oculta el error real | No se puede debuggear |
| 2 | Complica el diagnóstico | El log muestra rollback, no el comando que falló |
| 3 | Puede causar cascadas | Si rollback también falla, se pierde todo |
| 4 | No siempre es deseable | Fallo temporal (network) no requiere revert |
| 5 | Cambio destructivo implícito | El código cambia sin que el usuario lo decida |

---

## Arquitectura Propuesta

### Flow de Deploy Propuesto

```
git pull → install deps → migrate → build → restart → health check
                              ↓
                        si falla:
                          - guardar log detallado
                          - notificar error
                          - NO rollback automático
                          - dejar versión nueva instalada
                          - usuario decide qué hacer
```

### Comportamiento Post-Falla

- El deploy guarda el log completo
- Imprime mensaje claro con:
  - Qué falló
  - Dónde ver el log
  - Cómo hacer rollback manual si es necesario
- Deja el código en la versión nueva (parcialmente desplegado)
- El usuario decide si hacer rollback o reintentar

---

## Implementación

### Paso 1: Remover trap y manejo de errores manual

**Eliminar:**
```bash
trap rollback ERR
ROLLBACK_IN_PROGRESS=0
rollback() { ... }
```

**Reemplazar con:**
```bash
deploy() {
  log "=== Deploy iniciado: $(date) ==="

  # Git pull
  log "Obteniendo código..."
  git fetch origin
  git checkout "${REF}" || { log "ERROR: git checkout falló"; save_deploy_state "failed"; return 1; }
  git pull origin "${REF}" || { log "ERROR: git pull falló"; save_deploy_state "failed"; return 1; }

  # Install deps
  log "Instalando dependencias backend..."
  source .venv/bin/activate
  pip install -e . 2>&1 | tail -10 || { log "ERROR: pip install falló"; save_deploy_state "failed"; return 1; }

  # Migrate
  log "Ejecutando migraciones..."
  python -m alembic upgrade head || { log "ERROR: migration falló"; save_deploy_state "failed"; return 1; }

  # Build frontend
  log "Compilando frontend..."
  cd frontend
  if [ -f .env.production ]; then
    cp .env.production .env
  fi
  npm install 2>&1 | tail -5 || { log "ERROR: npm install falló"; save_deploy_state "failed"; return 1; }
  NODE_OPTIONS=--max-old-space-size=512 npm run build 2>&1 | tail -20 || { log "ERROR: npm build falló"; save_deploy_state "failed"; return 1; }
  cd ..

  # Restart
  log "Reiniciando servicios..."
  systemctl restart backend frontend || { log "ERROR: restart falló"; save_deploy_state "failed"; return 1; }

  # Health check
  log "Verificando servicios..."
  sleep 3
  for svc in backend frontend; do
    if ! systemctl is-active --quiet "colegios-$svc"; then
      log "ERROR: colegios-$svc no está corriendo"
      save_deploy_state "unhealthy"
      return 1
    fi
  done

  if ! curl -fsS --retry 3 --retry-delay 2 http://127.0.0.1:8000/api/v1/health; then
    log "WARN: API health check falló"
    log "La versión nueva está instalada pero el API no responde correctamente"
    log "Revisar: journalctl -u colegios-backend -n 50"
    save_deploy_state "unhealthy"
    return 1
  fi

  log "=== Deploy OK: $(date) ==="
  save_deploy_state "success"
  return 0
}
```

### Paso 2: Función para guardar estado

```bash
DEPLOY_LOG="/var/log/deploy.log"
DEPLOY_STATE="/tmp/deploy-last-state"

save_deploy_state() {
  local state=$1
  local commit=$(git rev-parse HEAD)
  local timestamp=$(date -Iseconds)

  echo "$state|$commit|$timestamp" > "$DEPLOY_STATE"

  # Log histórico
  echo "[$timestamp] $state|$commit" >> "$DEPLOY_LOG"
}
```

### Paso 3: Subcommands opcionales (rollback, status, retry)

```bash
case "${1:-deploy}" in
  deploy)
    deploy
    ;;
  rollback)
    echo "Último deploy: $(cat $DEPLOY_STATE)"
    echo "Para hacer rollback manual:"
    echo "  git checkout <commit-anterior>"
    echo "  ./scripts/deploy.sh"
    ;;
  status)
    echo "=== Estado ==="
    cat "$DEPLOY_STATE" 2>/dev/null || echo "Sin estado"
    systemctl status backend frontend --no-pager
    ;;
  retry)
    echo "Reintentando deploy..."
    deploy
    ;;
esac
```

---

## Estructura de Logs

```
/var/log/deploy.log          # Log histórico: [timestamp] status|commit
/tmp/deploy-last-state       # Estado actual: status|commit|timestamp
/tmp/deploy-YYYYMMDD-HHMMSS.log  # Log detallado del deploy actual
```

### Ejemplo de log histórico

```
[2026-08-24T03:12:01+0000] success|a1b2c3d
[2026-08-24T04:05:22+0000] failed|e5f6g7h
[2026-08-24T04:15:01+0000] unhealthy|i9j0k1l
```

---

## Beneficios

| Antes | Después |
|-------|---------|
| Fallo → rollback automático | Fallo → queda instalado, usuario decide |
| Error oculto | Error visible + log detallado |
| Debug difícil | Debug fácil: leer log |
| Cascada de fallos posible | Estado explícito |

---

## Testing

Para probar la nueva lógica sin afectar producción:

```bash
# En local o en VM de staging
cd /home/colegios/app
DEPLOY_REF=main ./scripts/deploy.sh deploy
```

---

## Rollback Manual

Si después de este cambio se necesita rollback:

```bash
# Ver commit anterior
git log --oneline -5

# Hacer checkout al commit anterior
git checkout <commit-anterior>

# Rebuild y restart
cd frontend && npm run build && cd ..
systemctl restart backend frontend
```

---

## Métricas de Éxito

- [ ] El deploy fallido ya no hace rollback automático
- [ ] El log contiene el error real que causó el fallo
- [ ] El usuario puede hacer rollback manual si lo desea
- [ ] El estado post-fallo permite reintentar sin perder trabajo
- [ ] Los comandos `status` y `rollback` funcionan
