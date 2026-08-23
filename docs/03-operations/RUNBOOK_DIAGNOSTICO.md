# Runbook: Diagnóstico de Infraestructura GCP

## Acceso rápido

```bash
# Variables
VM=colegios-server
ZONE=us-central1-a
PROJECT=my-project-colegios-chile
```

## 1. Estado de la VM

```bash
gcloud compute instances describe $VM --zone $ZONE --project $PROJECT \
  --format="table(status,zone,machineType,networkInterfaces[0].accessConfigs[0].natIP)"
```

## 2. Output del startup-script (consola serial)

```bash
gcloud compute instances get-serial-port-output $VM --zone $ZONE --project $PROJECT
```

Si el output es muy largo, buscar errores:

```bash
gcloud compute instances get-serial-port-output $VM --zone $ZONE --project $PROJECT 2>&1 | grep -iE "error|fail|fatal|warn" | tail -20
```

## 3. SSH directo para inspección

```bash
# Conectar y correr diagnóstico básico
gcloud compute ssh colegios@$VM \
  --zone $ZONE \
  --tunnel-through-iap \
  --ssh-key-file google_compute_engine \
  --command '
    echo "=== whoami ==="; whoami
    echo "=== /home ==="; ls -la /home/
    echo "=== /home/colegios ==="; ls -la /home/colegios/ 2>&1
    echo "=== /home/colegios/app ==="; ls -la /home/colegios/app/ 2>&1
    echo "=== .setup-complete ==="; ls -la /home/colegios/.setup-complete 2>&1
    echo "=== ps aux ==="; ps aux | grep -v grep | grep -E "apt|npm|node|postgres|nginx|startup" | head -20
    echo "=== uptime ==="; uptime
    echo "=== free ==="; free -m
    echo "=== df ==="; df -h
    echo "=== swapon ==="; swapon --show
  '
```

## 4. Logs del startup-script en la VM

```bash
# Si el usuario colegios tiene acceso a sudo para journalctl
gcloud compute ssh colegios@$VM \
  --zone $ZONE --tunnel-through-iap --ssh-key-file google_compute_engine \
  --command 'sudo journalctl -u google-startup-scripts --no-pager | tail -100'
```

```bash
# Log personalizado del nuevo startup.sh
gcloud compute ssh colegios@$VM \
  --zone $ZONE --tunnel-through-iap --ssh-key-file google_compute_engine \
  --command 'cat /var/log/startup.log 2>/dev/null || echo "No existe /var/log/startup.log"'
```

## 5. Verificar servicios activos

```bash
gcloud compute ssh colegios@$VM \
  --zone $ZONE --tunnel-through-iap --ssh-key-file google_compute_engine \
  --command '
    sudo systemctl status colegios-backend --no-pager --no-legend
    sudo systemctl status colegios-frontend --no-pager --no-legend
    sudo systemctl status nginx --no-pager --no-legend
    sudo systemctl status postgresql --no-pager --no-legend
  '
```

## 6. Smoke test manual

```bash
IP=$(gcloud compute addresses describe colegios-static-ip \
  --region us-central1 --project $PROJECT --format="value(address)")

# Health endpoint
curl -sf "http://${IP}/api/v1/health" | python3 -m json.tool

# Frontend
curl -sI "http://${IP}/" | head -5

# Backend API
curl -sf "http://${IP}/api/v1/" | head -5
```

## 7. Diagnosticos comunes

### Problema: `/home/colegios/app` no existe

**Causa probable**: El startup-script falló antes del paso de git clone.

**Diagnóstico**:
```bash
# Ver el log del startup
gcloud compute ssh colegios@$VM --zone $ZONE --tunnel-through-iap \
  --ssh-key-file google_compute_engine \
  --command 'cat /var/log/startup.log 2>/dev/null | grep -E "ERROR|FALLO"'
```

**Acción**: Corregir el error en `infra/startup.sh` y ejecutar `terraform taint` + reapply.

### Problema: PostgreSQL no arranca

```bash
gcloud compute ssh colegios@$VM --zone $ZONE --tunnel-through-iap \
  --ssh-key-file google_compute_engine \
  --command '
    sudo journalctl -u postgresql --no-pager | tail -30
    sudo systemctl status postgresql --no-pager
  '
```

### Problema: OOM (Out of Memory)

```bash
gcloud compute ssh colegios@$VM --zone $ZONE --tunnel-through-iap \
  --ssh-key-file google_compute_engine \
  --command '
    dmesg | grep -i "oom\|killed" | tail -10
    free -m
    swapon --show
  '
```

### Problema: apt lock

```bash
gcloud compute ssh colegios@$VM --zone $ZONE --tunnel-through-iap \
  --ssh-key-file google_compute_engine \
  --command '
    sudo fuser /var/lib/dpkg/lock* /var/lib/apt/lists/lock 2>/dev/null
    sudo killall -9 apt apt-get dpkg 2>/dev/null; sudo dpkg --configure -a
  '
```

## 8. Recrear VM (último recurso)

```bash
# Desde la máquina local con terraform
cd infra/
terraform taint google_compute_instance.colegios_server
terraform apply -var="plan_only=false"
```

O via GitHub Actions: ejecutar workflow "Infra GCP (manual)" con `recreate=true`.

## 9. Fallback: Packer (si el startup falla repetidamente)

Si el startup-script falla 3+ veces con el mismo error:

1. Considerar crear una imagen base con Packer
2. Instalar postgres, python, node, nginx en la imagen
3. Reducir el startup-script a solo: clone + deploy

Referencia: https://developer.hashicorp.com/packer/docs/builders/gce

## 10. Contactos de emergencia

| Rol | Contacto |
|-----|----------|
| DevOps | @rasgdev |
| GCP Project Owner | @rasgdev |
