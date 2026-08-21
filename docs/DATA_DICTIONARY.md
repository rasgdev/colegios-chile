# Diccionario de Datos

> Mapeo JSON de origen (MINEDUC SAE) → Parquet → PostgreSQL. Las columnas de
> PostgreSQL se documentan con su semántica y origen.

## Tablas de referencia (derivadas)

Derivadas de `sedes.parquet` durante la carga (`DISTINCT`), no requieren fuente propia.

| Tabla | Columnas | Origen |
|---|---|---|
| `regiones` | `codigo` (PK), `nombre` | `DISTINCT sedes(codigo_region, region)` |
| `comunas` | `codigo` (PK), `nombre`, `codigo_region` (FK) | `DISTINCT sedes(codigo_comuna, comuna, codigo_region)` |

## `establecimientos` (1 fila por RBD)

| Columna PG | Tipo | Origen JSON / nota |
|---|---|---|
| `rbd` | INTEGER (PK) | `rbd` |
| `nombre` | TEXT | `nombre` |
| `dependencia` | TEXT | `dependencia` |
| `telefono`, `mail`, `url` | TEXT | contacto |
| `habilitado_postular` | BOOLEAN | `habilitadoPostular` |
| `publicado` | BOOLEAN | `habilitadoVitrina` (renombrado). Filtro para mostrar/ocultar en el buscador. |
| `nivel_minimo` / `nivel_maximo` | TEXT | `nivelMinimo` / `nivelMaximo` (ej. PARVULARIO, BASICA, MEDIA) |
| `director` | TEXT | `director.nombre` (aplanado) |
| `etiquetas` | TEXT[] | `etiquetas` (CSV string → array; ej. `PIE,SEP,GRATUITO`) |
| `resumen_proyecto` | TEXT | `informacionInstitucional.resumenProyecto` |
| `documento_proyecto` / `documento_reglamento` | TEXT | URLs de documentos |
| `internado` / `integracion` / `subvencion_preferencial` / `peib` | BOOLEAN | flags de `informacionInstitucional` |
| `politica_uniforme` / `orientacion_religiosa` | TEXT | `informacionInstitucional` |
| `alumnos_matriculados` | INTEGER | matrícula total |
| `promedio_alumnos_por_curso` | FLOAT | `informacionInstitucional.promedioAlumnosPorCurso` |
| `cantidad_docentes` | INTEGER | n.º de docentes |
| `regimen` | TEXT | ⚠️ composición por sexo: `Mixto`, `Hombres`, `Mujeres` (NO es jornada JEC) |
| `busqueda_tsvector` | tsvector | **generado** (`f_busqueda_tsvector(nombre, resumen_proyecto, etiquetas)` con config `spanish_unaccent`) |

### Campos excluidos del schema

| Campo JSON | Motivo |
|---|---|
| `resumenProyectoPIE` | No aporta al buscador público |
| `procesosEspeciales` | Idem |
| `especialidades` | Idem |
| `distancia` | Artefacto del scrapeo (siempre 0) |
| `id_mongo` | Artefacto del scrapeo |

## `sedes` (1 fila por sede)

Clave compuesta `(rbd, codigo_sede)`. `codigo_sede` es **ordinal por colegio (1–4)**, no único global.

| Columna PG | Tipo | Nota |
|---|---|---|
| `rbd` + `codigo_sede` | INTEGER | PK compuesta |
| `codigo_region` / `codigo_comuna` | INTEGER | FK a `regiones` / `comunas` |
| `region` / `comuna` | TEXT | **snapshots del ETL** (denormalizados; se sobreescriben en cada recarga) |
| `calle` | TEXT | dirección |
| `latitud` / `longitud` | FLOAT | coordenadas (CHECK −90..90 / −180..180) |

## `cursos` (1 fila por curso/nivel)

Clave compuesta `(rbd, codigo_curso)`. ⚠️ `codigo_curso` es un código **compuesto de 12 dígitos** (ej. `811000000433`) que desborda `INTEGER`; se almacena como `BIGINT`.

FK compuesta `(rbd, codigo_sede) → sedes`. Incluye matrícula, copago
(`copago_cuotas`/`copago_valor`), cupos, vacantes, postulantes y proporciones
`porcentaje_cambio_*` (valores **0..1**, no 0..100).

## `indicadores` (EAV — set dinámico)

1 fila por clasificación de indicador. `tipo_indicador` (`SIMCE`,
`DESARROLLO_PERSONAL`, …) + `nombre_indicador` + `puntaje` (FLOAT) +
comparación con grupo socioeconómico (`comparacion_gse_numero`/`glosa`).

## `actividades` / `imagenes`

- `actividades`: extraprogramáticas (`tipo`, `nombre`, `nivel`, `exigencia`).
- `imagenes`: `nombre`, `url` (reservada, hoy `NULL`), `principal`. Ver `STORAGE.md`.
