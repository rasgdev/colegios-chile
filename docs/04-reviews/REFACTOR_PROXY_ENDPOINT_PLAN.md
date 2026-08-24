# Plan de Refactorización: API Proxy Endpoint

**Fecha:** 2026-08-24
**Estado:** Propuesto
**Prioridad:** Media (technical debt)

---

## Problema Actual

La solución actual detecta el contexto SSR vs browser para usar URLs diferentes:

```typescript
const getApiBase = (): string => {
  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000/api/v1";  // SSR
  }
  return import.meta.env.PUBLIC_API_BASE_URL || "/api/v1";  // Browser
};
```

### Issues identificados

1. **Antipattern de Astro** - Existe middleware de Astro para esto
2. **Fallback frágil** - Si la detección falla, usa localhost hardcodeado
3. **Acoplamiento implícito** - El código asume puerto 8000 para backend
4. **Duplicación de configuración** - `.env.production` + código

---

## Arquitectura Actual

```
Browser → Nginx (:80) → Astro (:4321) → [SSR fetch] → Backend (:8000)
Browser → Nginx (:80) → [API proxy] → Backend (:8000)
```

El browser usa `/api/v1` (relative, va por nginx), pero SSR necesita URL absoluta `http://127.0.0.1:8000/api/v1`.

---

## Solución Propuesta: API Proxy Endpoint

### Arquitectura Objetivo

```
Browser → Nginx (:80) → Astro (:4321) → /api/* → Backend (:8000)
```

Crear un endpoint catch-all en Astro que redirije al backend.

### Ventajas

- Una sola URL para todo: `/api/v1/...`
- No detección de contexto
- Consistencia total entre SSR y browser
- Mantenibilidad alta

### Desventajas

- ~5-10ms extra por request en páginas SSR
- Un hop adicional

**Tradeoff aceptable** para tráfico bajo y solo lectura.

---

## Implementación

### Paso 1: Crear endpoint proxy

**Archivo:** `frontend/src/pages/api/[...path].ts`

```typescript
import type { APIRoute } from "astro";

export const ALL: APIRoute = async ({ params, request }) => {
  const path = params.path;
  const search = request.url.includes('?') 
    ? '?' + new URL(request.url).search 
    : '';
  
  const url = `http://127.0.0.1:8000/api/v1/${path}${search}`;
  
  const response = await fetch(url, {
    method: request.method,
    headers: request.headers,
    body: request.method !== 'GET' ? request.body : undefined,
  });

  return new Response(response.body, {
    status: response.status,
    headers: response.headers,
  });
};
```

### Paso 2: Simplificar `api.ts`

```typescript
export const API_BASE = "/api/v1";
```

Eliminar toda la lógica de detección de contexto.

### Paso 3: Configurar nginx

Modificar `infra/startup.sh` para que nginx proxy `/api/` también en puerto 4321:

```nginx
server {
    listen 80;
    server_name _;

    # Proxy a frontend (Astro SSR)
    location / {
        proxy_pass http://127.0.0.1:4321;
        # ... headers ...
    }

    # Proxy a API (Backend FastAPI)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        # ... headers ...
    }
}
```

### Paso 4: Actualizar CORS

Ya no necesitamos CORS `*` en producción porque todas las requests quedan en el mismo dominio.

---

## Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `frontend/src/pages/api/[...path].ts` | Crear |
| `frontend/src/lib/api.ts` | Simplificar a `export const API_BASE = "/api/v1";` |
| `infra/startup.sh` | Actualizar config nginx |
| `src/api/main.py` | CORS más restrictivo en producción |

---

## Alternativas Consideradas

### Opción B: Modificar nginx para proxy en 4321

Hacer que nginx escuche en puerto 4321 también y proxy `/api/` ahí.

**Pros:** Más performante, menos hops
**Cons:** Cambios en nginx más invasivos

### Opción C: Usar variable SERVER_API_URL

```typescript
const getApiBase = (): string => {
  if (typeof window === "undefined") {
    return process.env.SERVER_API_URL || "http://127.0.0.1:8000/api/v1";
  }
  return import.meta.env.PUBLIC_API_BASE_URL || "/api/v1";
};
```

**Pros:** Más flexible que la actual
**Cons:** Sigue usando detección de contexto

---

## Criteria de Éxito

- [ ] SSR y browser usan la misma URL (`/api/v1`)
- [ ] No hay código de detección de contexto (`typeof window`)
- [ ] CORS en producción puede ser más restrictivo
- [ ] El fallback localhost ya no existe en producción
