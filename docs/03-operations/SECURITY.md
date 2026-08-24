# Seguridad de la API — Nota de hardening

> Base de conocimiento sobre el modelo de amenazas del API público y los controles
> aplicados (rate limiting, CORS) y por aplicar (X-Forwarded-For).

---

## 1. Modelo de amenazas

El API es **público, read-only y expone datos no sensibles** (catálogo MINEDUC).
No hay usuarios, roles ni endpoints de escritura (las escrituras van por el loader
ETL, no por HTTP).

Por lo tanto, el objetivo de seguridad no es la confidencialidad, sino:

1. **Abuso / DoS** — que un cliente sature el API.
2. **Lectura cross-origin desde el navegador** — que un sitio malicioso lea el API
   usando el navegador de una víctima.
3. **Integridad de los datos** — que nadie pueda alterar el catálogo vía HTTP.

---

## 2. Controles aplicados hoy

| Control | Estado | Detalle |
|---|---|---|
| Rate limiting por IP | ✅ | `slowapi` con `key_func=get_remote_address`. search/compare 30/min, resto 60/min |
| CORS | ✅ | `allow_credentials=False`; dev usa orígenes explícitos (`:4321`), prod sin cabeceras CORS (same-origin vía nginx), nunca wildcard |
| SQL injection | ✅ | Queries parametrizadas en `SearchService` (SQL dinámico = constantes hardcodeadas) |
| Validación de entrada | ✅ | Pydantic (`limit ge/le`, `offset ge`) + validación de dominio en use cases |
| Errores sin fuga | ✅ | `exceptions.py` → `{error, detail, status_code}` controlado, sin stack traces |
| Superficie write | ✅ Nula | Solo `GET`; sin endpoints de mutación |

---

## 3. X-Forwarded-For (XFF) — explicación básica

### El problema

Detrás de un reverse proxy (nginx/Caddy/load balancer), la conexión TCP **nunca
llega directa del usuario al app**:

```
usuario ──▶ nginx (proxy) ──▶ FastAPI
  200.1.2.3                     FastAPI ve: 127.0.0.1
```

`request.client.host` devuelve la IP del proxy, no la del visitante real.

### Qué es XFF

Header HTTP que el proxy agrega antes de reenviar la petición, con la IP original:

```
X-Forwarded-For: 200.1.2.3
```

Si hay varios proxies, cada uno agrega la IP anterior (cadena de IPs); la primera
es el cliente original.

### Distinción clave: header vs. conexión TCP

| Tipo | Dónde vive | ¿Falsificable? |
|---|---|---|
| IP en headers (`X-Forwarded-For`) | Texto HTTP que el cliente controla | ✅ Trivial (`curl -H`) |
| IP de la conexión TCP (`request.client.host`) | La calcula el SO al establecer la conexión | ❌ Difícil (requiere on-path / IP spoofing real) |

### Por qué el whitelist de "trusted proxies" no se puede suplantar

La regla NO es "¿el header dice X?", sino:

> "¿La conexión TCP viene de la IP de mi proxy? Si sí, leo `X-Forwarded-For`;
> si no, lo ignoro."

El whitelist compara contra la **IP de la conexión TCP**, no contra el header.
Si un atacante escribe `X-Forwarded-For: <ip-del-proxy>` pero se conecta desde su
propia IP, el app ve "fuente ≠ proxy" → ignora el header → queda rate-limitado por
su IP real. **No gana nada.**

Para engañar de verdad tendría que hacer que la **conexión TCP** llegue con la IP
del proxy como fuente (IP spoofing real): requiere estar en el camino (on-path /
MITM) o acceso a la red — si logra eso, el rate limiter es el menor de los problemas.

Con el proxy en **localhost** (`127.0.0.1`) o red Docker interna, los paquetes a esa
IP jamás salen de la máquina → la suplantación es imposible desde internet.

---

## 4. Gap detectado: rate limiting detrás de proxy

`limiter.py` usa `get_remote_address` (lee `request.client.host`). En producción
detrás de nginx, **todos** los clientes aparecen con la IP del proxy:

- El límite `30/minute` de `/search` se aplica **globalmente**: un usuario gasta 30
  peticiones y **bloquea a todos** (para FastAPI "todos son la misma IP").

### Fix (post-MVP / deployment)

1. `key_func` custom que respete `X-Forwarded-For`:
   ```python
   # src/api/limiter.py (futuro)
   def get_client_ip(request: Request) -> str:
       forwarded = request.headers.get("x-forwarded-for")
       if forwarded:
           return forwarded.split(",")[0].strip()
       return request.client.host if request.client else "unknown"
   ```
2. Levantar uvicorn con `--proxy-headers --forwarded-allow-ips 127.0.0.1` (solo el
   proxy de confianza; **nunca** rangos amplios de internet).
3. Limitar `/stats` (hoy sin rate limit; `/health` se deja abierto para healthchecks).

---

## 5. Por qué NO se usa API key / JWT

- El dato es público; no hay confidencialidad que proteger.
- Las React islands llaman al API **desde el navegador**: cualquier key quedaría
  expuesta en el Network tab → seguridad ilusoria.
- Una API key solo tiene sentido server-to-server (patrón BFF) o para un futuro
  "API público para desarrolladores" (clave = cuota/analytics), o endpoints de
  administración. Para el buscador actual: sobre-ingeniería.

**Regla de oro**: no exponer FastAPI directo a internet confiando en XFF; el
whitelist debe incluir SOLO el proxy (idealmente `127.0.0.1` o red Docker).

---

## 6. Checklist de hardening (futuro)

- [ ] `key_func` con `X-Forwarded-For` + `forwarded-allow-ips` restringido al proxy.
- [ ] Rate limit en `/stats`.
- [ ] TLS en el reverse proxy (deployment).
- [ ] `statement_timeout` en `asyncpg` (query FTS patológica).
- [ ] `Cache-Control` + ETag (F4) — reduce carga y mitiga abuso indirectamente.
- [ ] slowapi: considerar storage compartido si se corre multi-worker.
