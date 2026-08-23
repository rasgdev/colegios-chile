# Convenciones de la API

> Contrato y reglas de los endpoints `/api/v1/*`. Implementado en `src/api/`.

## Formato de error

Todos los errores usan un formato propio consistente (no RFC 7807 por simplicidad de MVP):

```json
{ "error": "<código>", "detail": "<mensaje>", "status_code": 400 }
```

| Caso | Código | HTTP |
|---|---|---|
| Parámetro inválido / validación | `peticion_invalida` | 400 |
| RBD no existe | `establecimiento_no_encontrado` | 404 |
| Más de 10 RBDs en compare | `demasiados_colegios` | 400 |
| Algún RBD de compare no existe | `colegios_no_encontrados` | 404 |
| Rate limit superado | `429` (slowapi) | 429 |

## Paginación

- `limit`: máximo **100**, default **20**. `limit > 100` → `400`.
- `offset`: default **0**, debe ser `>= 0`.
- Si `offset >= total`, se retorna `results: []` (no es error).

## Búsqueda (`GET /api/v1/search`)

- **Orden**: si hay `q`, por `ts_rank_cd(busqueda_tsvector, query)` DESC y luego `nombre` ASC
  (estable). Sin `q`, por `nombre` ASC.
- **Búsqueda vacía** (`q=` ausente o vacío): devuelve todos los resultados paginados.
- **Full-text**: `websearch_to_tsquery('spanish_unaccent', q)` sobre `busqueda_tsvector`.
  La configuración `spanish_unaccent` aplica `unaccent` + `spanish_stem`, por lo que
  `aleman` encuentra `Alemán`. Autocompletado y fuzzy están **fuera de alcance MVP**.

### Filtros

| Parámetro | Semántica |
|---|---|
| `dependencia` | Match exacto (case-insensitive): `PUBLICO`, `PARTICULAR SUBVENCIONADO`, `SERVICIO LOCAL DE EDUCACIÓN` |
| `regimen` | Match exacto (case-insensitive): `Mixto`, `Hombres`, `Mujeres` (composición por sexo, no jornada) |
| `nivel` | Categoría que el colegio **ofrece** según su rango `[nivel_minimo..nivel_maximo]` (ver abajo) |
| `copago_max` | Colegios con al menos un curso con `copago_valor <= copago_max` (subconsulta `EXISTS`, sin duplicados) |
| `etiquetas` | Match de array: `etiquetas @> ARRAY[...]` (el colegio tiene TODAS las etiquetas indicadas) |
| `comuna` | Match por nombre de comuna (`ILIKE %...%`) vía `EXISTS` sobre `sedes` |

### Semántica de `nivel`

`nivel_minimo`/`nivel_maximo` en los datos son **grados concretos** (`Pre-Kinder`,
`1º Básico`, ... `IV Medio`), no categorías. El filtro `nivel=` acepta una **categoría**
y el colegio matchea si su rango de grados intersecta la categoría:

| Categoría | Grados |
|---|---|
| `PARVULARIO` | `Pre-Kinder`, `Kinder` |
| `BASICA` | `1º Básico` … `8º Básico` |
| `MEDIA` | `I Medio` … `IV Medio` |

El orden de grados está definido en `src/domain/entities.py` (`NIVELES_ORDENADOS`).

## Recursos (`GET /api/v1/{sedes,cursos,indicadores,actividades,imagenes}?rbd=`)

- Retornan `200` con `[]` cuando el colegio existe pero no tiene datos de ese sub-recurso
  (degradación elegante).
- Retornan `404` solo cuando el `rbd` no existe en `establecimientos`.

`GET /api/v1/cursos/resumen?rbd=` devuelve un subconjunto esencial (payload liviano) para
la ficha: `codigo_curso`, `glosa_nivel`, `etiqueta_nivel`, `sexo`, `glosa_jornada`,
`copago_cuotas`, `copago_valor`, `cupos_totales`.

## Ficha (`GET /api/v1/establecimientos/{rbd}`)

Agregador backend: devuelve en una sola response `establecimiento` + `sedes` +
`cursos_resumen` + `indicadores` + `actividades` + `imagenes`. No expone el modelo ORM
completo; los DTOs están en `src/api/schemas/`.

## Comparación (`GET /api/v1/compare?rbds=1,2,3`)

- Máximo **10** RBDs separados por coma.
- Si alguno no existe → `404` con la lista de RBDs inválidos.
- Response: `establecimientos` + `indicadores` (por RBD) + `cursos_resumen` (por RBD).

## Rate limiting

Defensa en profundidad (slowapi, en memoria):

- `/search` y `/compare`: 30 req/min por IP.
- `/establecimientos*` y sub-recursos: 60 req/min por IP.

Superar el límite retorna `429` con headers `X-RateLimit-*`.

## Caching

Los datos de referencia (comunas/regiones) y `dataset_version` se cargan en el `lifespan`
de la app. El caching HTTP (ETag + 304) en recursos estables queda para F4.
