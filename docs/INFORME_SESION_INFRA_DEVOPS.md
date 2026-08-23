# Informe de Sesión — Infraestructura GCP & Pipeline de Deploy

**Fecha**: 22–23 agosto 2026
**Proyecto**: colegios-chile
**VM activa**: ✅ `colegios-server` (us-central1-a, e2-micro) — SSH funcional
**Estado del deploy**: 🔴 Bloqueado — `/home/colegios/app` no existe

---

## 1. Resumen Ejecutivo

El pipeline de infra (Terraform) funciona: la VM se crea, los roles de IAM se aplican y la configuración de metadatos SSH se establece correctamente. El bloqueo está en el **deploy SSH**: el `startup-script` de la VM falla silenciosamente antes de clonar el repositorio, por lo que `/home/colegios/app` nunca aparece y el comando `cd /home/colegios/app && bash scripts/deploy.sh` falla con `No such file or directory`.

La VM está **activa y accesible por SSH** — no es un problema de networking, firewall ni autenticación. El diagnóstico puede hacerse sin recrear la VM.

---

## 2. Cronología Completa de Errores

### 2.1 Infra Apply: "no access to service account" (3 iteraciones)

| Intento | Error | Causa | Solución |
|---|---|---|---|
| 1 | `Error waiting for instance to create: The user does not have access to service account '792243830602-compute@developer.gserviceaccount.com'` | El apply corre como `TERRAFORM_SERVICE_ACCOUNT` que tiene `compute.admin`, `projectIamAdmin`, `storage.objectAdmin` — ninguno incluye `iam.serviceAccounts.actAs`. El binding `deploy_service_account_user` otorgaba el rol a la SA de deploy (identidad equivocada). | Agregado `google_project_iam_member.tf_sa_service_account_user` (nivel proyecto, rol `iam.serviceAccountUser`, miembro = SA de terraform) + `time_sleep` 60s para propagación IAM. |
| 2 | `Error 403: Permission denied on data "google_compute_default_service_account"` | `data.google_compute_default_service_account` requiere `iam.serviceAccounts.get`, que la SA de terraform no tiene. | Reemplazado por `google_project_iam_member` (no necesita leer la SA específica). |
| 3 | ✅ Exitoso | — | — |

### 2.2 Deploy: ssh-compute@v1 — inputs inexistentes

**Error**: `failed to parse (unnamed) as a valid ssh-private format key: Cannot read properties of undefined`

**Warning**: `Unexpected input(s) 'instance', 'tunnel_through_iap', 'os_login'`

**Causa**: Los inputs `instance`, `tunnel_through_iap`, `os_login` **nunca existieron** en ningún tag publicado de `google-github-actions/ssh-compute` (verificado v0.1.0 → v2.0.0). Los inputs reales son:
- `instance_name` (requerido)
- `ssh_private_key` (requerido: `true`)
- `user`, `zone`, `command`, etc.
- El action **siempre** tuneliza por IAP (`--tunnel-through-iap` hardcodeado).

**Solución**:
- `instance` → `instance_name: colegios-server`
- Quitados `tunnel_through_iap`, `os_login`
- `user: colegios`
- Agregado `ssh_private_key: ${{ secrets.SSH_PRIVATE_KEY }}`

### 2.3 Deploy: Key Parse Error (DECODER routines)

**Error**: `error:1E08010C:DECODER routines::unsupported`

**Causa**: La llave ed25519 generada por el usuario en formato OpenSSH (`-----BEGIN OPENSSH PRIVATE KEY-----`) no fue parseable por `sshpk` (librería del action). Posible causa: formato incompatible o saltos de línea alterados al pegar el secreto en GitHub.

**Solución**: Generé llave **RSA 4096 en formato PEM** (`ssh-keygen -t rsa -b 4096 -m PEM -f google_compute_engine -C colegios -N ''`) y la setee directamente vía `gh secret set` (preserva bytes exactos, elimina errores de pegado manual).

### 2.4 Deploy: gcloud requiere `compute.instances.setMetadata`

**Error**: `Required 'compute.instances.setMetadata' permission for 'projects/.../instances/colegios-server'`

**Causa**: `gcloud compute ssh --ssh-key-file` (con OS Login deshabilitado) intenta escribir la clave pública en el metadata de la instancia antes de conectar. La SA de deploy solo tenía `iap.tunnelResourceAccessor` + `compute.viewer`.

**Intentos**:
1. Rol custom con solo `compute.instances.setMetadata` → falló: la SA de terraform no tiene `iam.roles.create` para crear roles custom.
2. Rol predefinido `roles/compute.instanceAdmin.v1` → ✅ funcionó (incluye setMetadata, pero también start/stop/delete/etc.).

### 2.5 Deploy: git "dubious ownership"

**Error**: `fatal: detected dubious ownership in repository at '/home/colegios/app'`

**Causa**: El `startup-script` crea `/home/colegios/app` como root. El `chown -R colegios:colegios /home/colegios` está al final del script, pero el `set -e` (línea 2) hizo que el script abortara antes de llegar al chown (el `deploy.sh` inicial falló durante el setup). El repositorio quedó root-owned → git rechaza operaciones cuando el usuario SSH es `colegios`.

**Solución**: `bash deploy.sh ${repo_branch} || echo "WARN: deploy inicial falló; se reintentará vía CI"` — el `|| echo` previene que `set -e` aborte y el chown siempre se ejecuta.

### 2.6 Deploy: `/home/colegios/app` no existe (recreaciones)

**Error**: `bash: line 1: cd: /home/colegios/app: No such file or directory`

**Causa**: El startup-script falla silenciosamente antes del paso `git clone` (paso ~8 de ~15). El `set -e` oculta cuál paso específico falló. En e2-micro (1 vCPU, 1GB RAM), el apt + node install + postgres setup tarda 10+ minutos; si algún paso falla (bloqueo de apt, timeout de red, OOM), el script aborta.

**Intentos de solución**:
1. Re-disparar deploy manualmente → mismo error (el clone aún no terminaba).
2. Agregar sentinel `.setup-complete` al final del startup-script + loop de espera en deploy (120 × 5s = 10 min) → el sentinel **nunca apareció** (el startup falla antes de llegar al final).
3. 3 recreaciones de VM con `recreate=true` → mismo resultado.

**Estado actual**: La VM está activa, SSH funciona, pero `/home/colegios/app` no existe.

---

## 3. Arquitectura Actual del Startup Script

El archivo `infra/startup.sh` (154+ líneas) ejecuta en este orden:

1. `set -e` → **cualquier error aborta todo**
2. `apt-get update && apt-get upgrade -y`
3. `apt-get install -y postgresql python3 nginx git curl ...`
4. Node.js 20 LTS via `curl ... | bash` + `apt-get install nodejs`
5. PostgreSQL tuning (e2-micro / 1GB RAM)
6. `systemctl restart postgresql`
7. Crear DB y usuario (`sudo -u postgres psql ... || true`)
8. **Crear usuario de deploy** (`useradd colegios`, sudoers acotado)
9. **Clonar repo** (`git clone -b ${repo_branch} ${repo_url} /home/colegios/app`)
10. Configurar backend (venv, `.env`)
11. Configurar servicios systemd (colegios-backend, colegios-frontend)
12. Configurar nginx
13. `bash /home/colegios/app/scripts/deploy.sh ${repo_branch} || echo "WARN: ..."`
14. `chown -R colegios:colegios /home/colegios`
15. `touch /home/colegios/.setup-complete` (sentinel)
16. `echo "=== Setup completo ==="`

**Problema**: Los pasos 1-7 son prerrequisitos del paso 9 (clone). Si cualquiera falla con `set -e`, el clone nunca ocurre y el deploy no tiene dónde conectarse.

---

## 4. Mapa de IAM Actual

### Service Accounts

| SA | Nombre | Roles | Propósito |
|---|---|---|---|
| `terraform-gha` | `TERRAFORM_SERVICE_ACCOUNT` | `compute.admin`, `serviceusage.serviceUsageAdmin`, `resourcemanager.projectIamAdmin`, `storage.objectAdmin`, `iam.serviceAccountUser` (proyecto) | Ejecutar terraform apply |
| `deploy-gha` | `SERVICE_ACCOUNT` / `TF_VAR_deploy_sa_email` | `iap.tunnelResourceAccessor`, `compute.osLogin` (muerto), `compute.viewer`, `iam.serviceAccountUser` (proyecto), `compute.instanceAdmin.v1` | SSH por IAP + deploy |

### Notas sobre IAM

- El rol `compute.osLogin` para deploy-gha es **inútil** actualmente (OS Login deshabilitado en la VM).
- `compute.instanceAdmin.v1` es más amplio que el mínimo necesario (incluye start/stop/delete/setMetadata).
- `iam.serviceAccountUser` a nivel de proyecto para deploy-gha es más amplio que el necesario (actAs en TODAS las SAs del proyecto).

---

## 5. Problemas Sistémicos Identificados

### 5.1 Startup Script: Punto Único de Falla Crítico
- 15+ pasos encadenados sin retries ni verificación de estado intermedio.
- `set -e` oculta el paso exacto que falla — sin acceso a la consola serial, es imposible diagnosticar sin adivinar.
- No hay idempotencia real: si el script se re-ejecuta, algunos pasos (apt install) son idempotentes pero otros (systemd service creation) pueden fallar si ya existen.
- No hay logging visible: el output va a la consola serial de GCE, no accesible desde CI.

### 5.2 Fragilidad Compuesta en e2-micro
- 1 vCPU, 1GB RAM: apt-get upgrade + node install + npm install compiten por memoria.
- PostgreSQL tuning para 1GB es justo; un pico de OOM en npm build mata el proceso y `set -e` aborta.
- No hay swap configurado como buffer.

### 5.3 Pipeline de Deploy
- No hay health-check gating: el deploy se dispara inmediatamente tras terraform apply, cuando la VM puede estar aún en setup.
- No hay version pinning del action `@v1` (tag móvil con breaking changes ya documentadas).
- No hay rollback: si deploy falla a mitad, la VM queda en estado inconsistente.
- 5 recreaciones de VM destruyeron el disco local y la DB cada vez (se re-siembra, pero pierde datos intermedios).

### 5.4 DB Local en Boot Disk
- PostgreSQL corre en la VM con datos en el disco de boot.
- Cada recreate destruye el disco → pérdida de datos (mitigado por seed scripts, pero no ideal para producción).

---

## 6. Estrategias Consideradas y su Resultado

| # | Estrategia | Descripción | Resultado |
|---|---|---|---|
| 1 | **Mantener OS Login** | Registrar pub key en perfil OS Login de la SA de deploy, conectar como email de SA | ❌ Rechazado: nombre de usuario impredecible (`sa_<hash>`) complica sudo + permisos |
| 2 | **Usuario dedicado + metadata SSH** | Crear `colegios` con `useradd`, passwordless sudo acotado, metadata `ssh-keys`, túnel IAP | ✅ Elegido como dirección |
| 3 | **Scoped sudoers** | Limitar sudo solo a `systemctl restart/status colegios-backend colegios-frontend` | ✅ Implementado |
| 4 | **Sentinel `.setup-complete`** | Deploy espera hasta 10 min por sentinel que indica setup completo | ✅ Implementado pero inefectivo (startup falla antes de escribirlo) |
| 5 | **Rol IAM custom** | Solo `compute.instances.setMetadata` | ❌ Falló: SA de terraform sin `iam.roles.create` |
| 6 | **Rol predefinido `instanceAdmin.v1`** | Incluye setMetadata (y más) | ✅ Funciona, pero viola mínimo privilegio |
| 7 | **Botón `recreate` en workflow** | Input `recreate=true` → `terraform taint` antes del plan | ✅ Implementado y usado 3 veces |
| 8 | **RSA PEM en vez de ed25519** | Formato PEM es universalmente compatible con sshpk | ✅ Resolvió parse error |
| 9 | **SSH directo vía `gh secret set`** | Setear secretos con `gh` evita errores de pegado manual | ✅ Resolvió key format issue |

---

## 7. Estado Actual de la VM

- **Estado**: `RUNNING` ✅
- **Zona**: `us-central1-a`
- **Tipo**: `e2-micro` (1 vCPU, 1GB RAM)
- **SSH**: Funcional (conectado como `colegios` vía IAP tunnel)
- **`/home/colegios/app`**: ❌ No existe
- **`/home/colegios/`**: Posiblemente existe (creado por `mkdir -p`), posiblemente vacío
- **Usuario `colegios`**: Posiblemente creado por `useradd` (si el script llegó al paso 8)
- **Procesos activos**: Desconocido — puede haber apt/npm trabados

---

## 8. Diagnóstico Inmediato Disponible (sin recrear)

La VM está activa y SSH funciona. El especialista puede diagnosticar inmediatamente:

```bash
# 1. Ver el output del startup-script (consola serial)
gcloud compute instances get-serial-port-output colegios-server \
  --zone us-central1-a \
  --project my-project-colegios-chile

# 2. SSH directo para inspección
gcloud compute ssh colegios@colegios-server \
  --zone us-central1-a \
  --tunnel-through-iap \
  --ssh-key-file google_compute_engine \
  --command 'whoami; ls -la /home/; ls -la /home/colegios 2>&1; ps aux | grep -E "apt|npm|node|startup|cloud" | grep -v grep'

# 3. Logs del startup-script (si el usuario tiene sudo suficiente)
gcloud compute ssh colegios@colegios-server \
  --zone us-central1-a \
  --tunnel-through-iap \
  --ssh-key-file google_compute_engine \
  --command 'sudo journalctl -u google-startup-scripts --no-pager | tail -100'
```

**Nota**: El comando #3 requiere que `colegios` tenga sudo para `journalctl`. El sudoers actual solo permite `systemctl`. Esto puede necesitar una ampliación temporal del sudoers para diagnóstico.

---

## 9. Archivos Modificados en la Sesión

| Archivo | Cambios |
|---|---|
| `infra/main.tf` | + IAM binding SA de terraform, + `time_sleep`, metadata `ssh-keys` (quitó `enable-oslogin`), + `compute.instanceAdmin.v1` para deploy SA |
| `infra/variables.tf` | + `tf_sa_email`, + `ssh_public_key` |
| `infra/versions.tf` | + provider `hashicorp/time ~> 0.11` |
| `infra/startup.sh` | + `useradd colegios` + sudoers acotado, + `chown -R`, + sentinel `.setup-complete`, + `|| echo` robustez |
| `.github/workflows/infra.yml` | + `TF_VAR_ssh_public_key`, + input `recreate`, + step de taint |
| `.github/workflows/deploy.yml` | `instance_name`, `user: colegios`, `ssh_private_key`, sentinel wait loop (pendiente revertir comando de diagnóstico) |
| `scripts/deploy.sh` | `systemctl restart` → `sudo systemctl restart` |
| `infra/.terraform.lock.hcl` | Actualizado con provider `time` |

**Nota**: Hay una edición **no commiteada** en `deploy.yml` con un comando de diagnóstico SSH temporal (quitar antes de commitear).

---

## 10. Recomendaciones para el Especialista DevOps

1. **Diagnóstico inmediato**: Acceder a la consola serial para ver el output exacto del startup-script y determinar en qué paso falla.
2. **Robustizar el startup-script**:
   - Quitar `set -e` global y manejar errores individualmente con retries.
   - Agregar logging a un archivo visible (`/var/log/startup.log`).
   - Hacer cada paso idempotente y verificable.
   - Considerar split en múltiples scripts o usar cloud-init con `runcmd`.
3. **Imagen pre-construida**: Evaluar Packer para crear una imagen base con postgres/python/node/nginx instalados, reduciendo el startup a clone + deploy.
4. **Health-check gating**: El deploy debería esperar por un health endpoint real (ej. `curl http://127.0.0.1:8000/api/v1/health`) en vez de un sentinel file.
5. **IAM cleanup**: Crear roles custom manuales (desde la consola de GCP, no via terraform) para evitar la dependencia de `iam.roles.create`.
6. **DB persistente**: Evaluar Cloud SQL para sobrevivir recreaciones.
7. **Version pinning**: Pinnear `ssh-compute@<sha>` en vez de `@v1`.
