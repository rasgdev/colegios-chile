# Estrategia de Carga de Datos

> Cómo los Parquet del ETL llegan a PostgreSQL. Decisión #14 de `ARCHITECTURE_v2.md`.

## Principio

Carga **atómica e idempotente** mediante **staging + swap transaccional**:

1. Los datos crudos se insertan en tablas `*_staging` (sin constraints salvo NOT NULL).
2. Se **valida** el contenido de staging antes de tocar las tablas finales.
3. Se ejecuta el **swap**: `TRUNCATE` de las tablas finales + `INSERT ... SELECT`
   desde staging, todo dentro de **una única transacción**.

Resultado: reejecutar `load_to_db.py` produce los mismos conteos, y una
interrupción a mitad de carga deja la base intacta (la transacción hace rollback).

## Orden de ejecución

```
make db-up      # levanta PostgreSQL (Podman)
make init-db    # crea rol + base de datos (idempotente)
make migrate    # alembic upgrade head (schema + staging)
make load-db    # Parquet → staging → validar → swap
```

| Script | Responsabilidad |
|---|---|
| `scripts/init_db.py` | Crea/verifica el **clúster** (rol + base de datos). NO toca schema. |
| Alembic (`make migrate`) | Gestiona el **schema**: tablas, constraints, FKs, índices, staging. |
| `scripts/load_to_db.py` | Carga los Parquet de `data/processed/latest/` a PostgreSQL. |

## Orden de carga (por dependencias de FK)

```
regiones → comunas → establecimientos → sedes → cursos → indicadores → actividades → imagenes
```

- `regiones` y `comunas` se **derivan** de `sedes.parquet` con `SELECT DISTINCT`
  sobre `(codigo_region, region)` y `(codigo_comuna, comuna, codigo_region)`.
- Verificado: la relación `codigo_comuna → (comuna, codigo_region)` es 1:1
  (344 comunas, 16 regiones).

## Transformaciones al cargar

| Origen (Parquet) | Destino (PostgreSQL) |
|---|---|
| `etiquetas` = CSV string (`"PIE,SEP"`) | `etiquetas TEXT[]` (`split(',')`; `NULL` → `[]`) |
| `habilitado_vitrina` | `publicado` (renombrado) |
| `distancia`, `id_mongo` | **excluidos** (artefactos del scrapeo) |
| `imagenes` (sin `url`) | `url` queda `NULL` (columna reservada) |
| `cursos.codigo_curso` (int64, 12 dígitos) | `BIGINT` (desborda `INTEGER`) |

## Validaciones post-carga (staging)

Antes del swap se verifica:

- Sin nulos en claves: `rbd`, `nombre`, `codigo_sede`, `codigo_curso`.
- Integridad referencial: `sedes.rbd ⊆ establecimientos.rbd`;
  `cursos.(rbd, codigo_sede) ⊆ sedes.(rbd, codigo_sede)`.
- Conteos mínimos razonables (establecimientos/sedes > 100).

Si falla alguna, el loader aborta **antes** del swap y la base queda como estaba.

## Conteos esperados (snapshot 2026-08-02)

| Tabla | Filas |
|---|---|
| regiones | 16 |
| comunas | 344 |
| establecimientos | 7,673 |
| sedes | 7,912 |
| cursos | 77,540 |
| indicadores | 49,830 |
| actividades | 206,041 |
| imagenes | 77,421 |
