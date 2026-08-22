# Plan de Hosting — Colegios de Chile

> **Stack**: Astro 7 (SSR Node.js) + FastAPI (Python) + PostgreSQL 15  
> **Dataset**: ~7.673 colegios, ~80 MB en PostgreSQL, tráfico estimado bajo-medio  
> **Fecha**: agosto 2026

---

## 1. Advertencia importante: Shared Hosting vs VPS

Si buscaste Hostinger probablemente viste planes desde **$2.99/mes** (Premium, Unlimited, Cloud Startup). **Eso es SHARED HOSTING, no VPS.**

| | **Shared Hosting** ($2.99-$7.99/mes) | **VPS KVM** ($6.49+/mes) |
|---|---|---|
| Acceso | Panel web. **No tienes root.** | SSH + root completo |
| Tecnologias | Solo **PHP** + MySQL | **Cualquiera**: Node.js, Python, PostgreSQL, Docker |
| Procesos persistentes | No puedes correr Node.js ni Python 24/7 | Si. FastAPI, Astro SSR, systemd |
| Ideal para | WordPress, landing PHP, portfolios estaticos | APIs, SSR, bases de datos, multi-site real |

**Tu proyecto necesita VPS.** Shared hosting NO puede correr FastAPI, Astro SSR ni PostgreSQL.

---

## 2. Opciones para tu stack (SSR + FastAPI + PostgreSQL)

### 2.1 VPS todo-en-uno (recomendado)

Un solo servidor con Ubuntu + Nginx + PostgreSQL + FastAPI + Astro SSR.

| Plataforma | Plan | vCPU | RAM | Storage | Precio/mes | DC Latam | Latencia Chile |
|---|---|---|---|---|---|---|---|
| **OVHcloud VPS-1** | 2027 range | 2 | **4 GB** | 40 GB NVMe | **$4.54** | No | ~220 ms |
| **Contabo VPS 10** | Cloud | 4 | **8 GB** | 75 GB NVMe | **~$5.00** (EUR 4.50) | No | ~200 ms |
| **Hostinger KVM 1** | VPS | 1 | 4 GB | 50 GB NVMe | **$6.49** | Sao Paulo | ~30-50 ms |
| **Vultr** | High Perf 1 GB | 1 | 1 GB | 25 GB NVMe | **$6.00** | Sao Paulo / Santiago | ~30-50 ms |
| **DigitalOcean** | Basic 1 GB | 1 | 1 GB | 25 GB SSD | **$6.00** | Sao Paulo | ~40-60 ms |
| **Hostinger KVM 2** | VPS | 2 | 8 GB | 100 GB NVMe | **$8.79** | Sao Paulo | ~30-50 ms |
| **Hetzner CX33** | Cloud | 2 | 4 GB | 40 GB NVMe | **$9.30** (EUR 8.49) | No | ~180 ms |
| **DigitalOcean** | Basic 2 GB | 1 | 2 GB | 50 GB SSD | **$12.00** | Sao Paulo | ~40-60 ms |
| **Vultr** | High Freq 2 GB | 1 | 2 GB | 50 GB NVMe | **$12.00** | Sao Paulo / Santiago | ~30-50 ms |

**Notas clave**:
- **OVHcloud VPS-1** ($4.54): El mas barato con 2 vCPU + 4 GB. Pero desde Europa. Ideal si no te importa latencia.
- **Contabo VPS 10** (~$5): 4 vCPU + 8 GB. Espectacular specs/precio. Pero tiene overselling conocido y fair usage en trafico. Performance inconsistente en horas pico. No para produccion critica.
- **Hostinger KVM 1** ($6.49): El equilibrio perfecto para Chile (DC Sao Paulo) + 4 GB RAM + panel simple. **Nuestra recomendacion principal.**
- **Vultr/DigitalOcean $6**: Solo 1 GB RAM. Es justisimo para correr PostgreSQL + Node + Python juntos. Recomendamos subir al plan de $12 (2 GB) para estar comodos.
- **Hostinger KVM 2** ($8.79): Doble de todo. Ideal si planeas montar multi-site (varios proyectos en el mismo servidor).

---

### 2.2 PaaS (sin configurar Linux)

| Plataforma | Costo/mes | Ideal si... |
|---|---|---|
| **Fly.io** (app + Postgres DIY) | **~$8-11** | No te importa gestionar backups de DB |
| **Railway** (Hobby) | **~$15-20** | Quieres deploy en 30 segundos |
| **Render** (Web + Postgres) | **~$21-28** | Quieres el PaaS mas simple y predecible |

**Contras de PaaS**: Cada sitio nuevo cuesta $7-$21/mes adicionales. No puedes hacer multi-site economico.

---

### 2.3 Cloud (AWS / GCP / Azure)

| Setup | Costo/mes | Ideal si... |
|---|---|---|
| **AWS EC2 t3.small** (self-managed DB) | ~$17-20 | Tienes creditos AWS o planeas escalar masivamente |
| **AWS EC2 + RDS** (DB gestionada) | ~$25-30 | Necesitas backups automaticos y HA |

**Contra principal**: Complejidad operativa alta para un proyecto simple. Overkill para tu escala.

---

## 3. Opcion 100% estatica — Costo $0

Si estas dispuesto a **eliminar el backend**, puedes servir todo de forma estatica y tu costo de hosting baja a **$0/mes**.

### Como funciona

1. **Convierte Astro a SSG** (output: 'static' en astro.config.mjs).
2. **Genera todas las fichas de colegios en build time** con getStaticPaths().
3. **La busqueda con filtros la haces en el navegador** usando MiniSearch (https://github.com/lucaong/minisearch) o un indice JSON precargado.
4. **Despliega** en Cloudflare Pages, Netlify, GitHub Pages o Vercel — todos tienen tier gratuito generoso.

### Costo

| Componente | Servicio | Costo |
|---|---|---|
| Hosting frontend | Cloudflare Pages / Netlify / GitHub Pages | **$0** |
| CDN global | Cloudflare (incluido) | **$0** |
| SSL | Let's Encrypt / Cloudflare (incluido) | **$0** |
| Backend | Ninguno | **$0** |
| Base de datos | Ninguna (indice JSON/Parquet en el cliente) | **$0** |
| **Total mensual** | | **$0** |
| Dominio .com (opcional) | Cloudflare Registrar | ~$11/ano |

### Que pierdes

- Busqueda full-text avanzada con PostgreSQL FTS (la reemplazas por busqueda client-side, suficiente para 7.6K registros).
- API REST con filtros dinamicos complejos.
- Comparador de colegios en tiempo real (puedes hacerlo client-side con JS).
- Ficha actualizada en tiempo real (debes hacer rebuild cuando cambien los datos).

### Cuando tiene sentido

- Si el dataset del MINEDUC se actualiza 1-2 veces al ano (cierto).
- Si tu prioridad es **costo cero** y aceptas que la busqueda sea 100% en el navegador.
- Para un MVP inicial antes de invertir en backend.

**Veredicto**: Es tecnicamente viable. Para 7.6K colegios, un indice MiniSearch de ~200 KB en el navegador permite busqueda instantanea con filtros. Es una opcion legitima si tu prioridad es el precio absoluto.

---

## 4. Multi-site en un VPS

Una gran ventaja del VPS es correr **varios sitios** pagando un solo hosting. Nginx redirige segun el dominio.

### Capacidad realista

| Plan | Sitios SSR + DB | Sitios estaticos |
|---|---|---|
| **OVHcloud VPS-1** (2 vCPU, 4 GB) | 2-3 | 10+ |
| **Hostinger KVM 1** (1 vCPU, 4 GB) | 2-3 | 10+ |
| **Contabo VPS 10** (4 vCPU, 8 GB) | 5-8 | 20+ |
| **Hostinger KVM 2** (2 vCPU, 8 GB) | 5-8 | 20+ |

### Costo por sitio adicional

| Concepto | Costo |
|---|---|
| Hosting | **$0** (ya pagado) |
| Dominio .com/.cl | **~$11/ano** (~$0.92/mes) |
| SSL (Let's Encrypt) | **$0** |
| **Total extra por sitio** | **~$0.90/mes** |

### Ejemplo: 3 proyectos en Hostinger KVM 1

```
colegios-chile.cl     -> Astro SSR + FastAPI + PostgreSQL   (:4321 / :8000)
mi-portafolio.com     -> Astro estatico (SSG)               (:3000)
blog-personal.cl      -> Ghost / WordPress                  (:2368)
------------------------------------------------------------------------
RAM usada: ~2.9 GB de 4 GB disponibles (sobra 1.1 GB)
```

---

## 5. Dominio

### 5.1 .cl vs .com

| TLD | Precio/ano | Donde registrar | Ideal si... |
|---|---|---|---|
| **.cl** | ~$11 USD ($9.990 CLP) | nic.cl | Audiencia 100% chilena |
| **.com** | $10.44 USD | Cloudflare Registrar | Alcance global, nombre mas disponible |

### 5.2 Registrars recomendados

| Registrar | .com 1er ano | .com renovacion | WHOIS Privacy | Nota |
|---|---|---|---|---|
| **Cloudflare** | $10.44 | $10.44 | Gratis | Precio de costo. Obliga usar su DNS (excelente). |
| **Porkbun** | $11.08 | $11.08 | Gratis | DNS flexible, interfaz moderna. |
| **Namecheap** | ~$5.98 | ~$13.98 | Gratis | Trampa: promo barata, renovacion cara. |
| **GoDaddy** | ~$2-5 | $21.99 | Pago | Evitar. Renovacion abusiva. |

**Trampa**: Namecheap/GoDaddy te atraen con precios bajos el primer ano y luego duplican/triplican la renovacion. Para un dominio que mantendras 3+ anos, Cloudflare o Porkbun son mas baratos en total.

### 5.3 Configuracion DNS recomendada

**Opcion A (Cloudflare — gratis y optimo)**:
1. Compra dominio en Cloudflare Registrar (o NIC.cl para .cl).
2. Apunta nameservers a Cloudflare (*.ns.cloudflare.com).
3. Activa proxy naranja (CDN) para tu dominio raiz.
4. Crea un registro A apuntando a la IP de tu VPS.
5. Crea un registro CNAME para www -> dominio raiz.
6. SSL/TLS en modo Full (strict) con certificado origin pull (gratis).

**Beneficios**: CDN global gratuito (cache estatico), DDoS protection basico, SSL automatico, y reduces la carga de tu VPS.

**Opcion B (DNS del registrar + Let's Encrypt)**:
- Usa los nameservers del registrar (NIC.cl, Porkbun, etc.).
- Configura un registro A directo a tu VPS.
- Instala Certbot en tu VPS para SSL gratuito con Let's Encrypt.
- Mas simple, pero sin CDN ni proteccion DDoS.

---

## 6. Costo total mensual (hosting + dominio)

| Opcion | Hosting/mes | Dominio/ano | Total/mes | Ano 1 total |
|---|---|---|---|---|
| **Opcion A: 100% estatico** | $0 | $11 (.com Cloudflare) | **~$0.90/mes** | ~$11 USD |
| **OVHcloud VPS-1** | $4.54 | $11 (.com Cloudflare) | **~$5.50/mes** | ~$66 USD |
| **Contabo VPS 10** | ~$5.00 | $11 (.com Cloudflare) | **~$5.90/mes** | ~$71 USD |
| **Hostinger KVM 1** | $6.49 | $11 (.com Cloudflare) | **~$7.40/mes** | ~$89 USD |
| **Hostinger KVM 2** | $8.79 | $11 (.com Cloudflare) | **~$9.70/mes** | ~$116 USD |
| **Hetzner CX33** | $9.30 | $11 (.com Cloudflare) | **~$10.20/mes** | ~$123 USD |
| **Render** (Web + Postgres) | $21 | $11 (.com Cloudflare) | **~$22/mes** | ~$264 USD |
| **Railway** (Hobby) | ~$18 | $11 (.com Cloudflare) | **~$19/mes** | ~$228 USD |
| **AWS EC2 t3.small** | ~$18 | $11 (.com Cloudflare) | **~$19/mes** | ~$228 USD |

> Nota: Dominio .cl desde NIC.cl cuesta ~$11 USD/ano. Dominio .com desde Cloudflare cuesta $10.44 USD/ano. La diferencia es marginal. Elige .cl si tu audiencia es 100% chilena; .com si quieres alcance global o un nombre mas corto/disponible.

---

## 7. Arquitectura de deploy sugerida (VPS todo-en-uno)

```
Usuario
   |
   v
+-------------------------------------+
|  Nginx (reverse proxy + HTTPS)      |
|  +-- /  -> Astro SSR (Node.js :4321)  |
|  +-- /api -> Uvicorn (FastAPI :8000)  |
+-------------------------------------+
   |
   v
+-------------------------------------+
|  PostgreSQL 15 (localhost :5432)    |
|  Dataset precargado (7.673 colegios)|
+-------------------------------------+
```

### Pasos de deploy (resumen)

1. **Provisionar VPS** con Ubuntu 24.04 LTS.
2. **Instalar dependencias**: node 20+, python 3.12+, postgres 15, nginx, certbot.
3. **Clonar repo**, instalar dependencias Python (pip install -e .) y Node (npm install).
4. **Cargar base de datos**: make init-db migrate load-db (o restaurar un dump).
5. **Configurar systemd services** para FastAPI (uvicorn) y Astro (node ./dist/server/entry.mjs).
6. **Configurar Nginx** como reverse proxy con SSL (Let's Encrypt).
7. **Configurar firewall** (ufw): solo 22, 80, 443.

> Nota de seguridad: Revisa docs/SECURITY.md antes de exponer la API publica. Asegurate de que el rate limiting (slowapi) y CORS esten configurados correctamente.

---

## 8. Veredicto final

### Opcion A: Quiero costo cero (o casi cero)

| Componente | Costo |
|---|---|
| **Astro SSG** + MiniSearch (client-side) | $0 |
| **Cloudflare Pages** (hosting) | $0 |
| **Dominio .com** (Cloudflare Registrar) | $10.44/ano |
| **Total mensual** | **~$0.90/mes** |
| **Total ano 1** | **~$11 USD** |

**Elegir si**: Tu prioridad absoluta es el precio. Aceptas que la busqueda y los filtros corran en el navegador. El dataset se actualiza pocas veces al ano.

---

### Opcion B: Quiero lo mas barato con mi stack actual (SSR + API + DB)

| Componente | Costo |
|---|---|
| **OVHcloud VPS-1** (2 vCPU, 4 GB) | $4.54/mes |
| **Dominio .com** (Cloudflare Registrar) | $10.44/ano |
| **CDN + DNS + SSL** (Cloudflare) | $0 |
| **Total mensual** | **~$5.40/mes** |
| **Total ano 1** | **~$65 USD** |

**Elegir si**: No te importa la latencia desde Europa (~220ms). Quieres el VPS mas barato con specs decentes. Incluye backup diario gratuito.

---

### Opcion C: Mejor para Chile + multi-site (RECOMENDACION PRINCIPAL)

| Componente | Costo |
|---|---|
| **Hostinger KVM 1** (1 vCPU, 4 GB) | $6.49/mes |
| **Dominio .com** (Cloudflare Registrar) | $10.44/ano |
| **CDN + DNS + SSL** (Cloudflare) | $0 |
| **Total mensual** | **~$7.36/mes** |
| **Total ano 1** | **~$88 USD** |

**Elegir si**: Tu audiencia esta en Chile/Latam. Quieres latencia baja (DC Sao Paulo). Planeas montar 2-3 sitios mas en el mismo VPS. Quieres un panel simple sin complicaciones.

---

### Opcion D: Maximas specs por precio (con riesgo)

| Componente | Costo |
|---|---|
| **Contabo VPS 10** (4 vCPU, 8 GB) | ~$5.00/mes |
| **Dominio .com** (Cloudflare Registrar) | $10.44/ano |
| **Total mensual** | **~$5.90/mes** |
| **Total ano 1** | **~$71 USD** |

**Elegir si**: Quieres montar 5-8 sitios en un solo servidor. Aceptas el riesgo de throttling y performance inconsistente en horas pico. No es para proyectos criticos.

---

### Opcion E: Cero Linux (PaaS)

| Componente | Costo |
|---|---|
| **Render** (Web + Postgres) | $21/mes |
| **Dominio** | ~$11/ano |
| **Total mensual** | **~$22/mes** |

**Elegir si**: Valoras tu tiempo por encima de $15/mes. No quieres tocar un terminal en tu vida.

---

## 9. Comparativa multi-site: 3 sitios

| Plataforma | Sitio 1 | Sitio 2 | Sitio 3 | **Total/mes** |
|---|---|---|---|---|
| **Contabo VPS 10** | $5.00 | $0 | $0 | **$5.00** + dominios |
| **Hostinger KVM 1** | $6.49 | $0 | $0 | **$6.49** + dominios |
| **Render** (1 servicio c/u) | $21 | $21 | $21 | **$63/mes** |
| **Railway** (1 servicio c/u) | ~$18 | ~$18 | ~$18 | **~$54/mes** |

> Con un VPS, hospedar 3 sitios cuesta lo mismo que hospedar 1. La unica diferencia es el dominio (~$0.90/mes cada uno).

---

## 10. Cuando reconsiderar

- Si el trafico supera ~10.000 visitas/dia -> escalar a KVM 4 (Hostinger) o migrar a AWS con load balancer.
- Si necesitas alta disponibilidad (99.9%+) -> AWS con RDS Multi-AZ + EC2 auto-scaling.
- Si el equipo crece y necesita deploys sin friccion -> Railway o Render Pro.
- Si quieres expandir a otros paises con CDN propio -> Considerar Cloudflare Pro ($20/mes) o AWS CloudFront.

---

*Precios verificados agosto 2026. Los valores en USD pueden variar segun tipo de cambio. Siempre revisa la pagina oficial antes de comprar.*
