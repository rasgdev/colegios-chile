# Plan de Deploy — GCP e2-micro (Costo $0/mes)

> **Objetivo**: Hostear Colegios de Chile en Google Cloud Platform usando la instancia e2-micro dentro del free tier permanente.
> **Stack**: Astro 7 (SSR Node.js) + FastAPI (Python) + PostgreSQL 15
> **Costo estimado**: $0/mes (VM) + ~$11/ano (dominio)
> **Fecha**: agosto 2026

---

## 1. Resumen ejecutivo

| Concepto | Valor |
|---|---|
| **Instancia** | GCP Compute Engine e2-micro |
| **Specs** | 0.25 vCPU (shared), 1 GB RAM, 30 GB disco |
| **Region** | us-central1 (Iowa) — free tier |
| **Costo VM** | **$0/mes** (free tier permanente, 730 horas/mes) |
| **Costo dominio** | ~$11/ano (Cloudflare .com o NIC.cl .cl) |
| **Costo egress** | $0 (1 GB/mes incluido) |
| **Costo total mes** | **~$0.90/mes** (solo dominio) |
| **Costo total ano 1** | **~$11 USD** |

### Limitaciones clave

- **1 GB RAM**: Tu stack consume ~500 MB. Sobran ~500 MB para el SO y picos.
- **Sin Docker**: El daemon de Docker consume ~200 MB que no tienes.
- **Sin multi-site**: No hay RAM para montar otros proyectos.
- **Latencia**: ~120-150 ms desde Iowa a Chile.
- **0.25 vCPU shared**: Suficiente para trafico bajo.

---

## 2. Huella de recursos del proyecto

Basado en analisis real del codigo y datos.

### Disco

| Componente | Disco en prod |
|---|---|
| Ubuntu 24.04 LTS | ~1.5 GB |
| PostgreSQL 15 | ~100 MB |
| Base de datos colegios | ~25-30 MB |
| Python venv (backend) | ~200-250 MB |
| Astro dist/ | ~10 MB |
| Nginx | ~10 MB |
| Logs + temporales | ~50 MB |
| **Total** | **~1.9-2.0 GB** |
| **Disponible** | **30 GB** |

### RAM

| Componente | RAM estimada |
|---|---|
| Ubuntu servicios base | ~200 MB |
| PostgreSQL tuneado | ~80-100 MB |
| FastAPI/Uvicorn | ~50-80 MB |
| Astro SSR (Node.js) | ~80-120 MB |
| Nginx | ~10-20 MB |
| **Total** | **~420-520 MB** |
| **Disponible** | **1,024 MB** |
| **Sobra** | **~500 MB** |

---

## 3. Prerequisitos

1. Cuenta Google Cloud (nueva o existente). Free tier no expira.
2. Tarjeta de credito para verificar la cuenta.
3. Dominio registrado (Cloudflare, Porkbun o NIC.cl).
4. SSH key para acceder a la VM.

---

## 4. Setup paso a paso

### 4.1 Crear proyecto en GCP

```bash
gcloud projects create colegios-chile --name="Colegios Chile"
gcloud config set project colegios-chile
```

### 4.2 Habilitar Compute Engine

```bash
gcloud services enable compute.googleapis.com
```

### 4.3 Crear la instancia e2-micro

```bash
gcloud compute instances create colegios-server \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard \
  --tags=web-server
```

**Notas**:
- `us-central1-a` es una de las 3 regiones que califica para free tier.
- `pd-standard` (HDD) es gratis dentro del free tier.
- El disco de 20 GB es mas que suficiente (tu app usa ~2 GB).

### 4.4 Configurar firewall

```bash
gcloud compute firewall-rules create allow-http-https \
  --allow=tcp:80,tcp:443 \
  --target-tags=web-server

gcloud compute firewall-rules create allow-ssh \
  --allow=tcp:22 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=web-server
```

### 4.5 Conectarse a la VM

```bash
gcloud compute ssh colegios-server --zone=us-central1-a
```

### 4.6 Ejecutar setup automatizado

```bash
scp scripts/setup-gcp.sh colegios-server:/tmp/
gcloud compute ssh colegios-server --zone=us-central1-a --command="bash /tmp/setup-gcp.sh"
```

---

## 5. Configuracion de PostgreSQL

El script `setup-gcp.sh` configura PostgreSQL automaticamente. Configuracion manual en `/etc/postgresql/15/main/postgresql.conf`:

```ini
shared_buffers = 64MB
effective_cache_size = 128MB
work_mem = 4MB
maintenance_work_mem = 32MB
max_connections = 20
wal_buffers = 4MB
checkpoint_completion_target = 0.9
listen_addresses = 'localhost'
```

Reiniciar: `sudo systemctl restart postgresql`

**Consumo**: ~60-80 MB RAM (vs ~200 MB default).

---

## 6. Configuracion de la aplicacion

### 6.1 Clonar el repo

```bash
cd /var/www/colegios-chile
git clone https://github.com/tu-usuario/colegios-chile.git .
```

### 6.2 Instalar dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-prod.txt
```

### 6.3 Compilar frontend

```bash
cd frontend && npm install && npm run build && cd ..
```

### 6.4 Variables de entorno

```bash
cat > .env.production << 'EOF'
DATABASE_URL=postgresql+asyncpg://colegios:colegios@localhost:5432/colegios
API_PORT=8000
FRONTEND_PORT=4321
API_BASE_URL=https://apisae.mineduc.cl
COMUNAS_API_URL=https://api.baseapi.cl/api/v1/sii/datos/comunas
MAX_CONCURRENT_REQUESTS=5
REQUEST_DELAY_SECONDS=1.0
MAX_RETRIES=5
REQUEST_TIMEOUT=30
LOG_LEVEL=WARNING
EOF
```

### 6.5 Cargar la base de datos

```bash
source .venv/bin/activate
make init-db migrate load-db
```

---

## 7. Servicios systemd

### 7.1 FastAPI backend

```bash
sudo cat > /etc/systemd/system/colegios-api.service << 'EOF'
[Unit]
Description=Colegios Chile API (FastAPI)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=colegios
WorkingDirectory=/var/www/colegios-chile
Environment=PATH=/var/www/colegios-chile/.venv/bin
ExecStart=/var/www/colegios-chile/.venv/bin/uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5
MemoryMax=256M
MemoryHigh=200M

[Install]
WantedBy=multi-user.target
EOF
```

### 7.2 Astro SSR frontend

```bash
sudo cat > /etc/systemd/system/colegios-web.service << 'EOF'
[Unit]
Description=Colegios Chile Frontend (Astro SSR)
After=network.target

[Service]
Type=simple
User=colegios
WorkingDirectory=/var/www/colegios-chile/frontend
Environment=NODE_ENV=production
Environment=HOST=127.0.0.1
Environment=PORT=4321
ExecStart=/usr/bin/node ./dist/server/entry.mjs
Restart=always
RestartSec=5
MemoryMax=256M
MemoryHigh=200M

[Install]
WantedBy=multi-user.target
EOF
```

### 7.3 Activar servicios

```bash
sudo systemctl daemon-reload
sudo systemctl enable colegios-api colegios-web
sudo systemctl start colegios-api colegios-web
sudo systemctl status colegios-api colegios-web
```

---

## 8. Configuracion de Nginx

```bash
sudo cp scripts/nginx-gcp.conf /etc/nginx/sites-available/colegios-chile
sudo sed -i 's/TU_DOMINIO/tudominio.cl/g' /etc/nginx/sites-available/colegios-chile
sudo ln -sf /etc/nginx/sites-available/colegios-chile /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Verificar:
```bash
curl -s http://localhost | head -20
curl -s http://localhost/api/v1/health | python3 -m json.tool
```

---

## 9. SSL con Let's Encrypt

```bash
sudo certbot --nginx -d tudominio.cl -d www.tudominio.cl
sudo certbot renew --dry-run
```

---

## 10. DNS (Cloudflare)

1. Obtener IP externa de la VM:
```bash
gcloud compute instances describe colegios-server \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

2. En Cloudflare: DNS > Add record > Type A, Name: @, Content: [tu IP], Proxy: on.
3. En Cloudflare: SSL/TLS > Full (Strict).

---

## 11. Deploy y actualizaciones

```bash
#!/bin/bash
# deploy.sh — Ejecutar en el servidor
set -e
cd /var/www/colegios-chile
git pull origin main
source .venv/bin/activate
pip install -q -r requirements-prod.txt
cd frontend && npm install -q && npm run build && cd ..
make migrate 2>/dev/null || true
sudo systemctl restart colegios-api colegios-web
echo "Deploy completado!"
```

---

## 12. Monitoreo

```bash
# Estado de servicios
sudo systemctl status colegios-api colegios-web postgresql nginx

# Uso de RAM
free -h

# Uso de disco
df -h /

# Logs en tiempo real
sudo journalctl -u colegios-api -f
sudo tail -f /var/log/nginx/access.log
```

---

## 13. Backup de la base de datos

```bash
# Backup manual
pg_dump -U colegios colegios > /var/www/colegios-chile/backups/colegios_$(date +%Y%m%d).sql

# Backup automatico (cron diario a las 3 AM)
echo "0 3 * * * pg_dump -U colegios colegios > /var/www/colegios-chile/backups/colegios_\$(date +\%Y\%m\%d).sql" | sudo crontab -
```

> Google Cloud no incluye backups automaticos en el free tier. Gestionalo manualmente o usa un bucket de Cloud Storage (5 GB gratis).

---

## 14. Ruta de escalamiento

| Nivel | Trigger | Solucion | Costo |
|---|---|---|---|
| **0** | Dataset actual, bajo trafico | e2-micro (actual) | $0/mes |
| **1** | Trafico > 1.000 visitas/dia | e2-small (2 GB RAM) | ~$7.70/mes |
| **2** | Trafico > 5.000 visitas/dia | e2-medium (4 GB RAM) | ~$15.40/mes |
| **3** | Trafico > 20.000 visitas/dia | Hostinger KVM 2 o e2-standard-2 | ~$25-50/mes |

Para escalar:
```bash
gcloud compute instances set-machine-type colegios-server \
  --machine-type=e2-small \
  --zone=us-central1-a
```

---

## 15. Comparativa final: GCP e2-micro vs Hostinger KVM 1

| Factor | GCP e2-micro | Hostinger KVM 1 |
|---|---|---|
| **Costo** | **$0/mes** | $6.49/mes |
| **RAM** | 1 GB | 4 GB |
| **vCPU** | 0.25 shared | 1 dedicada |
| **Latencia Chile** | ~120-150 ms | ~30-50 ms |
| **Disco** | 30 GB | 50 GB |
| **Docker** | No | Si |
| **Multi-site** | No | Si (2-3 sitios) |
| **Backups auto** | No | Si (semanales) |
| **Escalabilidad** | GCP nativo | Manual |
| **Complejidad** | Media | Baja |
| **Ano 1 total** | **~$11 USD** | **~$88 USD** |

**Gana GCP e2-micro si**: Prioridad es costo $0, no necesitas multi-site, aceptas latencia de ~150 ms.

**Gana Hostinger KVM 1 si**: Quieres latencia baja para Chile, multi-site, Docker, y margen de RAM para crecer.

---

*Plan creado agosto 2026. Precios de GCP verificados en cloud.google.com/compute. El free tier de e2-micro es permanente y no expira.*
