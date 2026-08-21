# Plan de ETL: Colegios de Chile

## 1. Objetivo

Construir un dataset histórico de establecimientos educacionales de Chile, extrayendo datos de forma controlada desde la API pública del MINEDUC y almacenándolos en archivos Parquet para análisis interno.

## 2. Fuentes de datos

| Endpoint | Descripción | Volumen estimado |
| --- | --- | --- |
| `GET https://apisae.mineduc.cl/sae-api-vitrina/v1/establecimientos?comuna={COMUNA}` | Lista de establecimientos por comuna | ~346 requests |
| `GET https://apisae.mineduc.cl/sae-api-vitrina/v1/establecimientos/{RBD}` | Detalle completo por RBD | ~10.000 requests |

### Listado de comunas

Se obtiene desde:

- `https://api.baseapi.cl/api/v1/sii/datos/comunas`

Se normaliza y se hace un **discovery** de variantes aceptadas por la API de MINEDUC.

## 3. Stack tecnológico

| Componente | Uso |
| --- | --- |
| `httpx` | Requests HTTP asíncronos |
| `asyncio` + `asyncio.Semaphore` | Control de concurrencia |
| `tenacity` | Reintentos con backoff y jitter |
| `polars` | Transformación y manipulación de datos |
| `pyarrow` | Escritura de archivos Parquet |
| `pydantic` | Validación de estructura de los datos |
| `pydantic-settings` | Configuración por variables de entorno |
| `duckdb` | Validaciones de calidad de datos |
| `structlog` | Logging estructurado en JSON |
| `tqdm` | Barra de progreso en terminal |
| `pytest` | Tests unitarios |

## 4. Arquitectura del proyecto

```text
colegios-chile/
├── .env.example
├── .gitignore
├── Dockerfile
├── Makefile
├── README.md
├── plan.md
├── requirements.txt
├── requirements-dev.txt
├── config/
│   └── settings.py
├── data/
│   ├── raw/
│   │   ├── comunas/
│   │   └── establecimientos/
│   └── processed/
│       └── YYYY-MM-DD/
├── logs/
│   └── etl_YYYY-MM-DD_HH-MM-SS.jsonl
├── notebooks/
│   └── 01_validacion.ipynb
├── scripts/
│   ├── discover_comunas.py
│   └── run_etl.py
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── rate_limiter.py
│   ├── extract/
│   │   ├── __init__.py
│   │   ├── comunas.py
│   │   └── detalle.py
│   ├── transform/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── normalizers.py
│   ├── load/
│   │   ├── __init__.py
│   │   └── parquet.py
│   ├── validation/
│   │   ├── __init__.py
│   │   └── duckdb_checks.py
│   └── state.py
├── tests/
│   ├── fixtures/
│   │   ├── comuna_recoleta.json
│   │   └── detalle_8997.json
│   ├── test_api_client.py
│   ├── test_comuna_normalization.py
│   └── test_transform.py
└── assets/
    └── comunas_mapeo.json
```

## 5. Flujo del pipeline

### Paso 1: Discovery de comunas

Ejecutar `scripts/discover_comunas.py` una vez o cuando se actualice el catálogo.

1. Obtener listado de comunas desde `api.baseapi.cl`.
2. Normalizar nombres:
   - Mayúsculas.
   - Sin tildes.
   - Espacios → guiones bajos.
   - Quitar apóstrofos.
   - Juntar palabras repetidas como `BIO BIO` → `BIOBIO`.
   - Quitar guiones: `TIL-TIL` → `TILTIL`.
3. Probar cada comuna contra `apisae.mineduc.cl`.
4. Para las que fallen, probar variantes:
   - Quitar `PUERTO ` → `NATALES`.
   - Probar con/sin `DE`, `LA`, `LAS`, `LOS`, `DEL`.
5. Guardar `assets/comunas_mapeo.json`.

### Paso 2: Extracción

Ejecutar `scripts/run_etl.py`.

1. Cargar `assets/comunas_mapeo.json`.
2. Cargar `data/state.json` si existe (checkpointing).
3. Para cada comuna no procesada:
   - GET lista de establecimientos.
   - Guardar JSON en `data/raw/comunas/`.
   - Extraer lista de RBDs.
4. Para cada RBD no descargado:
   - GET detalle.
   - Guardar JSON en `data/raw/establecimientos/`.
   - Actualizar `data/state.json`.
5. Si el proceso se interrumpe, al reiniciar continúa desde el último estado.

### Paso 3: Transformación

1. Leer todos los JSON raw de comunas.
2. Leer todos los JSON raw de detalle.
3. Validar estructura con Pydantic.
4. Normalizar en 6 DataFrames de Polars.

### Paso 4: Carga

1. Escribir 6 archivos Parquet en `data/processed/YYYY-MM-DD/`.
2. Crear symlink o copia en `data/processed/latest/`.

### Paso 5: Validación

1. Ejecutar consultas DuckDB sobre los archivos Parquet.
2. Verificar:
   - Integridad referencial entre tablas.
   - No duplicados en RBDs.
   - No valores nulos en columnas clave.
   - Conteos razonables.
3. Guardar resultado de validaciones en `logs/`.

### Paso 6: Reporte

Generar `data/processed/YYYY-MM-DD/report.json` con:

- Tiempo de ejecución.
- Comunas totales, exitosas, fallidas.
- RBDs totales, exitosos, fallidos.
- Requests totales, 429, 5xx.
- Tiempo promedio de respuesta.
- Bytes descargados.
- Filas por tabla Parquet.

## 6. Estructura de salida Parquet

### 6.1. Tablas relacionadas

| Archivo | Granularidad | Claves |
| --- | --- | --- |
| `establecimientos.parquet` | 1 fila por RBD | `rbd` |
| `sedes.parquet` | 1 fila por sede | `rbd`, `codigo_sede` |
| `cursos.parquet` | 1 fila por curso/nivel | `rbd`, `codigo_sede`, `codigo_curso` |
| `actividades.parquet` | 1 fila por actividad | `rbd` |
| `indicadores.parquet` | 1 fila por clasificación | `rbd` |
| `imagenes.parquet` | 1 fila por imagen | `rbd` |

### 6.2. Historial

Cada ejecución genera una carpeta `data/processed/YYYY-MM-DD/` con los 6 archivos. También se mantiene `data/processed/latest/` apuntando a la última corrida exitosa.

## 7. Concurrencia y control de carga

- **Máximo 5 workers asíncronos** con `asyncio.Semaphore`.
- **Delay base de 1 segundo** entre requests por worker.
- **Rate limiting adaptativo**:
  - Si se detecta `429 Too Many Requests`, reducir workers a 2 y aumentar delay.
  - Si se detectan múltiples 5xx consecutivos, pausar 30 segundos.
  - Si el tiempo promedio de respuesta supera 2 segundos, reducir concurrencia.
- **Reintentos con backoff exponencial y jitter**:
  - Máximo 5 reintentos.
  - `delay = min(2^attempt + random(), 60)` segundos.
- **User-Agent neutro**:
  - `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`

## 8. Manejo de errores

- **HTTP 400 en comuna:** registrar en `logs/`, continuar.
- **HTTP 429 / 503:** backoff adaptativo, reintentar.
- **HTTP 5xx:** reintentar con backoff, si persiste marcar como fallido.
- **JSON inválido:** guardar en `logs/invalid/`, continuar.
- **RBD fallido:** no detener el pipeline. Se reporta al final.
- **Proceso interrumpido:** se reanuda desde el checkpoint `data/state.json`.

## 9. Configuración

Variables de entorno o archivo `.env`:

```env
API_BASE_URL=https://apisae.mineduc.cl
COMUNAS_API_URL=https://api.baseapi.cl/api/v1/sii/datos/comunas
MAX_CONCURRENT_REQUESTS=5
REQUEST_DELAY_SECONDS=1.0
MAX_RETRIES=5
REQUEST_TIMEOUT=30
RAW_DIR=data/raw
PROCESSED_DIR=data/processed
LOGS_DIR=logs
STATE_FILE=data/state.json
LOG_LEVEL=INFO
USER_AGENT=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

## 10. Logging

- Logging estructurado en JSON.
- Cada log incluye: `timestamp`, `level`, `component`, `comuna`, `rbd`, `status_code`, `duration_ms`, `error`.
- Archivo: `logs/etl_YYYY-MM-DD_HH-MM-SS.jsonl`.

## 11. Validaciones DuckDB

Ejemplos de consultas a ejecutar:

```sql
-- Integridad referencial: sedes -> establecimientos
SELECT s.rbd
FROM sedes.parquet s
LEFT JOIN establecimientos.parquet e ON s.rbd = e.rbd
WHERE e.rbd IS NULL;

-- Integridad referencial: cursos -> sedes
SELECT c.rbd, c.codigo_sede
FROM cursos.parquet c
LEFT JOIN sedes.parquet s
  ON c.rbd = s.rbd AND c.codigo_sede = s.codigo_sede
WHERE s.rbd IS NULL;

-- RBDs duplicados
SELECT rbd, COUNT(*) AS n
FROM establecimientos.parquet
GROUP BY rbd
HAVING n > 1;

-- Establecimientos sin sedes
SELECT e.rbd
FROM establecimientos.parquet e
LEFT JOIN sedes.parquet s ON e.rbd = s.rbd
WHERE s.rbd IS NULL;
```

## 12. Tests

- `test_api_client.py`: reintentos, rate limiting, headers.
- `test_comuna_normalization.py`: casos especiales de nombres de comuna.
- `test_transform.py`: JSON → DataFrames con fixtures.

Fixtures incluirán respuestas reales de:

- `comuna=RECOLETA`
- `detalle del RBD 8997`

## 13. Orquestación

### Makefile

```makefile
install:
	pip install -r requirements.txt

test:
	pytest

discover:
	python scripts/discover_comunas.py

etl:
	python scripts/run_etl.py

validate:
	python -m src.validation.duckdb_checks

all: install discover etl validate
```

### Dockerfile

Opcional, para reproducibilidad total del entorno.

## 14. Consideraciones éticas y legales

- Los datos provienen de una API pública del MINEDUC.
- Uso exclusivamente interno.
- No se extraen datos personales individuales.
- Se recomienda revisar los términos de uso de `apisae.mineduc.cl` si en el futuro se publica el dataset.

## 15. Decisiones clave

| Tema | Decisión |
| --- | --- |
| Stack | Python + `httpx` + `asyncio` + `polars` + `pyarrow` + `duckdb` |
| Extracción | Híbrida: full la primera vez, luego checkpointing con reintentos |
| Concurrencia | 5 workers + rate limiting adaptativo |
| Errores | Continuar y reportar |
| User-Agent | Neutro |
| Historial | Sí, carpetas por fecha + `latest/` |
| Validaciones | DuckDB |
| Tests | Sí, con fixtures |
| Configuración | Variables de entorno via `pydantic-settings` |
