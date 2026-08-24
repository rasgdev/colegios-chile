# Plan: API base URL SSR / browser

**Fecha:** 2026-08-24  
**Estado:** Propuesto  
**Prioridad:** Media (technical debt)  
**Supersede:** borrador inicial “API Proxy Endpoint” (proxy catch-all en Astro) — **descartado**

---

## 1. Problema actual

La arquitectura de red en producción ya es correcta. El único punto frágil es cómo el frontend elige la base URL de la API según el runtime.

```text
Browser  → Nginx:80 /api/  → FastAPI:8000     ✅ ya OK
Browser  → Nginx:80 /      → Astro:4321       ✅
Astro SSR → hardcode http://127.0.0.1:8000/api/v1  ⚠️ deuda
```

Código actual (`frontend/src/lib/api.ts`):

```typescript
const getApiBase = (): string => {
  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000/api/v1";  // SSR hardcode
  }
  if (import.meta.env.PUBLIC_API_BASE_URL) {
    return import.meta.env.PUBLIC_API_BASE_URL;
  }
  return "/api/v1";
};
```

### Issues

1. **Hardcode de red en lógica** — puerto 8000 y host loopback pegados al código.
2. **Detección frágil** — `typeof window` en lugar de `import.meta.env.SSR` (API de Astro).
3. **Duplicación de config** — `.env.production` + fallback en código.
4. **CORS en prod incoherente** — `allow_origins=["*"]` con `allow_credentials=True` en `src/api/main.py` (inválido/inseguro); no es el foco del hardcode pero se corrige en el mismo refactor.

### Quién consume la API hoy

| UI | Archivo | Runtime del fetch | ¿Le afecta el hardcode SSR? |
|----|---------|-------------------|-----------------------------|
| Ficha `/colegio/{rbd}` | `pages/colegio/[rbd].astro` → `getFicha` | **SSR (Node)** | **Sí** |
| Búsqueda | `SearchPage.tsx` | Browser (isla `client:load`) | No |
| Filtros región/comuna | `Filters.tsx` → `getRegiones` / `getComunas` | Browser | No |
| Comparar | `ComparePage.tsx` | Browser | No |

**Único consumidor SSR de la API hoy:** la ficha. Search, compare y combos región/comuna corren en el navegador y ya usan `/api/v1` (nginx en prod).

---

## 2. Principio de diseño

Cada capa hace su trabajo. No se inventa un proxy extra en Astro.

| Runtime | URL base | Fuente |
|---------|----------|--------|
| Browser | `/api/v1` | relativa (nginx en prod; vite proxy o `PUBLIC_*` en dev) |
| Astro SSR (Node) | `http://127.0.0.1:8000/api/v1` | env **no pública** `INTERNAL_API_BASE_URL` |

```text
PLAN OBJETIVO
═════════════

  Browser ──/api/v1──► Nginx:80 ──► FastAPI:8000
                                      ▲
  Astro SSR ──INTERNAL_API_BASE_URL───┘
              (env; loopback; no pasa por nginx)
```

- **Nginx** sigue siendo el único reverse proxy público (`/` → Astro, `/api/` → FastAPI). Ya está en `infra/startup.sh`.
- **No** crear `frontend/src/pages/api/[...path].ts`.
- **No** hacer que nginx escuche en 4321.

---

## 3. Por qué se descarta el proxy catch-all en Astro

El borrador inicial proponía un BFF en `pages/api/[...path].ts` para “una sola URL”.

| Idea del borrador | Realidad |
|-------------------|----------|
| “Una sola URL unifica SSR y browser” | En Node, `fetch("/api/v1")` es relativa **sin origin** → falla o no es lo que se cree. SSR igual necesita URL absoluta por detrás. |
| “Middleware de Astro resuelve esto” | El middleware actual solo pone headers de seguridad; no es el patrón para base URL de API. |
| “Más simple” | Añade hop, reenvío de headers/body/métodos y el hardcode se mueve al proxy. |
| e2-micro (1 GB) | Doble trabajo en la misma VM sin beneficio. |
| Nginx ya proxya `/api/` | El Paso “configurar nginx para /api/” del borrador **ya está hecho**. |

El proxy Astro solo tendría sentido si **no** hubiera reverse proxy delante. No es el caso.

---

## 4. Flujos (referencia)

### 4.1 Ficha SSR — comportamiento actual

```text
1. Usuario → misitio.cl/colegio/8506
2. Nginx (path página) → Astro :4321
3. [rbd].astro llama getFicha(8506)
4. getApiBase(): typeof window === undefined
   → hardcode http://127.0.0.1:8000/api/v1
5. fetch directo loopback → FastAPI
6. Astro arma HTML → browser
```

### 4.2 Ficha SSR — objetivo

```text
1–3. igual
4. getApiBase(): import.meta.env.SSR
   → INTERNAL_API_BASE_URL (env; default dev = loopback :8000)
5–6. igual en red; el destino es config, no lógica escondida
```

### 4.3 Browser (búsqueda, filtros, comparar) — sin cambio de red

```text
React island → fetch("/api/v1/...") → Nginx → FastAPI
```

Regiones/comunas (`Filters.tsx` + TanStack Query) van por este camino tras `client:load` en `index.astro`.

---

## 5. Cómo debe quedar cada pieza

### 5.1 `frontend/src/lib/api.ts`

```typescript
function getApiBase(): string {
  if (import.meta.env.SSR) {
    return (
      process.env.INTERNAL_API_BASE_URL ??
      "http://127.0.0.1:8000/api/v1"
    );
  }
  return import.meta.env.PUBLIC_API_BASE_URL || "/api/v1";
}

export const API_BASE = getApiBase();
```

- Preferir `import.meta.env.SSR` sobre `typeof window`.
- En SSR se lee `process.env.INTERNAL_API_BASE_URL` (runtime). **No** usar
  `import.meta.env.INTERNAL_API_BASE_URL`: en Astro 7 `import.meta.env.X` se
  inlinea en build, con lo que el valor quedaría fijado y systemd no tendría
  efecto.
- `process.env.INTERNAL_API_BASE_URL` vive dentro de la rama `import.meta.env.SSR`
  (estática `false` en el cliente), así que el bundle del browser no referencia
  `process` (rama eliminada por tree-shaking).
- Fallback localhost solo si falta env (dev local).
- Contrato de `fetchJson` / search / ficha / etc. sin cambios.

### 5.2 `frontend/src/env.d.ts`

```typescript
/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly PUBLIC_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare namespace NodeJS {
  interface ProcessEnv {
    readonly INTERNAL_API_BASE_URL?: string;
  }
}
```

### 5.3 Variables de entorno frontend

`PUBLIC_*` se **inlinea en build** (disponible en browser y server); la var
privada `INTERNAL_API_BASE_URL` se lee en **runtime** vía `process.env` (solo
server). En prod el server standalone no carga `.env` en runtime, así que la
fuente real de `INTERNAL_API_BASE_URL` es systemd (véase 5.5), no
`.env.production`.

| Archivo | Contenido objetivo |
|---------|-------------------|
| `frontend/.env.example` | `PUBLIC_API_BASE_URL=` (vacío → default `/api/v1` + proxy vite) y `INTERNAL_API_BASE_URL=http://127.0.0.1:8000/api/v1` (solo dev) |
| `frontend/.env.production` | `PUBLIC_API_BASE_URL=/api/v1`. **Sin** `INTERNAL_API_BASE_URL` (quedaría muerta; en prod la provee systemd) |
| `frontend/.env` (local, gitignored) | Alinear con example (solo dev) |

### 5.4 `frontend/astro.config.mjs` — proxy solo en dev

```javascript
vite: {
  plugins: [tailwindcss()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
},
```

En `astro dev`, el browser usa `/api/v1` (relativa, same-origin) sin CORS al
:8000 (equivalente local de nginx). **No** existe la opción "sin proxy vite": el
CSP `connect-src 'self'` (y CORS) bloquearían un fetch directo a
`http://localhost:8000` desde el browser.

### 5.5 `infra/startup.sh` — systemd frontend

Añadir al unit `colegios-frontend` (junto a `HOST` / `PORT` / `NODE_ENV`):

```ini
Environment=INTERNAL_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Esta es la **fuente de verdad en prod**: el server standalone lee
`process.env.INTERNAL_API_BASE_URL` en runtime (no carga `.env`).

**Nginx en el mismo script: no modificar** el split `location /` vs `location /api/` (ya correcto).

### 5.6 CORS — `config/settings.py` + `src/api/main.py`

**settings** (fuente única de verdad del backend):

```python
# CSV de orígenes; vacío = defaults según environment
cors_origins: str = ""
```

**main.py:**

- `allow_credentials=False` (la app es same-origin vía nginx y no usa cookies/sesión).
- Si `cors_origins` no vacío → parsear CSV (orígenes explícitos).
- Si vacío y `development` → `http://localhost:4321`, `http://127.0.0.1:4321`.
- Si vacío y `production` → lista vacía (sin cabeceras CORS). Same-origin vía
  nginx no necesita CORS; nunca `["*"]`.
- Renombrar `PRODUCTION_ORIGINS` → `DEV_ORIGINS` (hoy guarda orígenes de dev).

Documentar en `.env.example` (raíz):

```env
CORS_ORIGINS=https://TU_IP_O_DOMINIO
```

### 5.7 Explicitamente fuera de alcance

| Pieza | Motivo |
|-------|--------|
| `frontend/src/pages/api/[...path].ts` | No crear |
| Cambiar `location /api/` en nginx | Ya correcto |
| Rate limit / X-Forwarded-For | Otro ticket (`docs/03-operations/SECURITY.md`) |
| Contrato de endpoints API | Sin cambios |
| `typeof window` en `ComparePage` (localStorage) | No es API base |

---

## 6. Archivos a modificar (implementación)

| Archivo | Cambio |
|---------|--------|
| `frontend/src/lib/api.ts` | `getApiBase` con `import.meta.env.SSR` + `process.env.INTERNAL_API_BASE_URL` |
| `frontend/src/env.d.ts` | tipar `PUBLIC_*` (ImportMetaEnv) + `INTERNAL_*` (NodeJS.ProcessEnv) |
| `frontend/.env.example` | documentar `PUBLIC_*` + `INTERNAL_*` |
| `frontend/.env.production` | solo `PUBLIC_API_BASE_URL=/api/v1` |
| `frontend/astro.config.mjs` | proxy vite `/api` en dev |
| `infra/startup.sh` | `INTERNAL_API_BASE_URL` en unit frontend |
| `config/settings.py` | `cors_origins` |
| `src/api/main.py` | CORS sin `*` en prod (`allow_credentials=False`, lista vacía en prod); leer settings; renombrar `PRODUCTION_ORIGINS` → `DEV_ORIGINS` |
| `.env.example` (raíz) | documentar `CORS_ORIGINS` |

Este documento (`docs/04-reviews/REFACTOR_PROXY_ENDPOINT_PLAN.md`) es la especificación; no requiere renombrarlo para ejecutar el trabajo.

---

## 7. Orden de implementación

1. `api.ts` + `env.d.ts` + `.env*` frontend  
2. `astro.config.mjs` proxy dev  
3. `startup.sh` env systemd  
4. `settings` + `main.py` CORS + `.env.example` raíz  
5. Smoke / criterios de éxito  

---

## 8. Criterios de éxito

- [ ] Sin `typeof window` para elegir API base  
- [ ] Browser en prod: Network muestra requests a `/api/v1/...` (same-origin)  
- [ ] SSR ficha (`/colegio/{rbd}`): HTML 200 con datos  
- [ ] `INTERNAL_API_BASE_URL` configurable; hardcode solo como default de dev  
- [ ] CORS prod sin `*` (`allow_credentials=False`, lista vacía en prod salvo `CORS_ORIGINS` explícito)  
- [ ] Dev: `make frontend` + backend sin pelea CORS (proxy vite)  
- [ ] No existe endpoint proxy catch-all en Astro  

### Pruebas mínimas

1. Abrir ficha SSR → 200 + contenido.  
2. Search island → XHR a `/api/v1/search?...`.  
3. Combos región/comuna → `/api/v1/regiones` y `/api/v1/comunas?region=`.  
4. Backend caído → ficha degrada con error controlado (no hang eterno).  
5. `curl -H "Origin: https://evil.example" -I` a la API en prod → sin `Access-Control-Allow-Origin: *`.  

### Rollback

- Revertir `api.ts` + env frontend + línea systemd.  
- CORS y nginx son cambios independientes y reversibles por commit.

---

## 9. Alternativas (histórico)

| Opción | Veredicto |
|--------|-----------|
| **A (esta)** — `INTERNAL_API_BASE_URL` + browser relativo + nginx | **Elegida** |
| **B** — Proxy catch-all en Astro | Descartada (no arregla SSR relativo; hop extra; hardcode se mueve) |
| **C** — Solo nginx en 4321 además de 80 | Descartada / confusa; el split en :80 ya es el diseño correcto |
| **D** — Seguir con `typeof window` + hardcode | Status quo; no aceptable a medio plazo |

---

## 10. Resumen en una frase

Separar browser vs SSR con config explícita (`PUBLIC_*` / `INTERNAL_*`), reutilizar el proxy nginx que ya existe, arreglar CORS de producción, y no añadir un BFF en Astro que no resuelve el problema y solo suma complejidad en una VM pequeña.
