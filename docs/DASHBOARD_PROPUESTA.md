# Propuesta de mejora: "Convivencia escolar" — decidir colegio con datos

> Idea de mejora (pendiente de implementación). Refuerza la misión del producto:
> ayudar a familias chilenas a elegir colegio, convirtiendo el dato de
> **Clima de convivencia escolar** (hoy enterrado en la ficha como semáforo
> aislado) en capacidades de decisión.
>
> Estado: **propuesta**. Fecha: 2026-08-21.

---

## 1. El norte

El dato de `Clima de convivencia escolar` (y sus 3 pares IDPS: autoestima,
hábitos, participación) es de los más relevantes para elegir colegio y hoy solo
se ve en la ficha como un semáforo "vs GSE". La propuesta lo convierte en
**tres features de valor**, priorizando la **comuna** (unidad real de decisión
de una familia), no la región.

## 2. Contexto del dato (cómo se determina)

- `Clima de convivencia escolar` es un **Indicador de Desarrollo Personal y
  Social (IDPS)** publicado por la **Agencia de Calidad de la Educación / MINEDUC**.
- Es un índice de **percepción** (no prueba objetiva), construido con los
  *Cuestionarios de Calidad y Contexto* aplicados junto al Simce a
  **estudiantes (~50%), apoderados (~40%) y docentes (~10%)**.
- Tres subdimensiones: **Ambiente de respeto · Ambiente organizado · Ambiente seguro**.
- `puntaje` escala ~0–100; `comparacion_gse_glosa` = `Más alto / Similar / Más bajo`
  **respecto a colegios del mismo Grupo Socioeconómico (GSE)**.
- Ver `docs/INDICADORES.md` para el detalle de los IDPS y del GSE.

## 3. Limitaciones (honestidad con el usuario)

- **Snapshot único** (2026-08-02): todo es **comparativo** (ranking + "vs GSE"),
  no hay tendencia interanual.
- Es **percepción**, no medida dura → etiquetar como "percepción de la comunidad
  escolar", no "calidad objetiva".
- `comparacion_gse_glosa` trae valores sucios (`No es posible comparar…`, `""`,
  `NA`) → agrupar los 3 principales + bucket "No comparable".
- Comunas con pocos colegios → mostrar `n_colegios` y advertir cuando la muestra
  es pequeña (evitar falsa precisión).

---

## 4. Features propuestas (priorizadas)

### Feature 1 — Filtro "Convivencia destacada" en el buscador ★

**Valor**: la familia convierte "quiero buen ambiente" en un criterio seleccionable.

- Checkbox *"Convivencia escolar destacada"* en `Filters.tsx`.
- Filtra colegios con `Clima de convivencia escolar` **"Más alto"** que su GSE.

**Backend**:
- `src/domain/entities.py`: campo `convivencia_destacada: bool` en `SearchQuery`.
- `src/application/search.py`: normalizar el flag.
- `src/api/routers/search.py`: parámetro `convivencia_destacada: bool = False`.
- `src/infrastructure/search_service.py::_build_where`: `EXISTS` sobre
  `indicadores` (`nombre_indicador='Clima de convivencia escolar' AND
  comparacion_gse_glosa='Más alto'`).

**Frontend**: `api.ts` (`SearchParams`), `Filters.tsx`, `format.ts` (si aplica).

### Feature 2 — Contexto "tu colegio vs tu zona" en la ficha ★★

**Valor**: responde *"¿es bueno comparado con mis alternativas reales (comuna/región)?"*,
no vs. un GSE abstracto.

- En `colegio/[rbd].astro`, junto a cada indicador: puntaje del colegio +
  **promedio de su comuna** + **promedio de su región**.

**Backend**:
- `src/application/ficha.py`: usar la `Sede` principal (comuna/región) y pedir promedios.
- `src/infrastructure/db/repositories.py`: nuevo `SqlDashboardRepository` con
  `promedio_por_comuna(nombre_indicador, comuna)` y `promedio_por_region(...)`
  (agregación `AVG(puntaje)` sobre `indicadores ⋈ sedes`).
- `src/domain/entities.py`: `Ficha` + campo `contexto: list[ContextoIndicador]`.
- `src/api/schemas/establecimientos.py`: DTO correspondiente.

> Nota: `nivel_indicador` (Básica/Media) se promedia en conjunto por colegio.

### Feature 3 — Página "Panorama de mi zona" ★★★

**Valor**: apoderados, comunidad y prensa responden *"¿cómo está la convivencia
en mi comuna?"*. Entrada **centrada en "mi zona"**, no ranking nacional.

- Nueva ruta `/panorama`: input de comuna (reusa `Combobox` + `getComunas`).
- Distribución **"Más alto / Similar / Más bajo"** de los 4 IDPS (barra apilada, Recharts).
- Puntaje promedio por indicador (comuna vs. región vs. nacional, barras agrupadas).
- **Ranking de colegios destacados** de la comuna (top por clima escolar) con
  enlace a su ficha.

**Backend** — nuevo `src/api/routers/dashboard.py`:
- `GET /api/v1/dashboard/zona?comuna=<nombre>` →
  `{ comuna, region, indicadores: [{nombre, promedio, n_colegios,
  distribucion:{mas_alto,similar,mas_bajo,no_comparable}}],
  top_colegios: [{rbd, nombre, puntaje_clima}] }`.
- `GET /api/v1/dashboard/zona?region=<codigo>` → mismo shape a nivel región.
- DTOs en `src/api/schemas/dashboard.py`; agregación en `SqlDashboardRepository`.
- Registrar en `ALL_ROUTERS` + `apply_etag` (dataset estático) + rate limit.

**Frontend**:
- Añadir `recharts` a `frontend/package.json`.
- `frontend/src/pages/panorama.astro` + island `PanoramaPage.tsx` (TanStack Query).
- `api.ts`: `getDashboardZona()` + tipos regenerados con `openapi-typescript`.
- Enlace "Panorama" en `Header.astro`.

---

## 5. Orden de implementación sugerido

1. **Backend de agregación** (`SqlDashboardRepository` + endpoint `zona`) — base de las 3.
2. **Feature 1** (filtro) — quick win, alto valor.
3. **Feature 2** (contexto en ficha).
4. **Feature 3** (página panorama + Recharts).

## 6. Verificación

`pytest` (unit domain + API con DB de test para agregaciones), `make backend` /
`make frontend`, `npm run lint` / `npm run typecheck`.

## 7. Fuentes

- Agencia de Calidad de la Educación — Otros Indicadores de Calidad (IDPS).
- `docs/INDICADORES.md` (glosario y subdimensiones).
- `docs/ARCHITECTURE_v2.md` (§6 API endpoints, decisión #16 sobre mapas).
