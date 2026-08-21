# Known Issues — Dataset

> Limitaciones y gotchas conocidos del dataset MINEDUC. Actualizado 2026-08-20.

## Cobertura

- **344/346 comunas** cubiertas (objetivo F0: ≥300). Las 2 faltantes:
  - **TREHUACO** (Región de Ñuble): sin RBDs en SAE; la API no devuelve establecimientos.
  - **ANTARTICA** (Antártica): la API responde pero con 0 RBDs.
- 16 regiones · 7,673 RBDs · snapshot **2026-08-02** (instantánea; la fecha debe mostrarse en el frontend).

## Estructura de datos

- **`codigo_sede` y `codigo_curso` NO son únicos globalmente.** `codigo_sede` tiene solo 4 valores (1–4, ordinal de sede por colegio) y `codigo_curso` 497 (código de nivel que se repite entre colegios). La clave correcta es compuesta: `sedes(rbd, codigo_sede)` y `cursos(rbd, codigo_curso)`. Ver `ARCHITECTURE_v2.md` §4.
- **`etiquetas` en Parquet es CSV string** (`"PIE,SEP"`), no array. El loader (F1) hace `split(',')`. Ver decisión #21 de v2.
- `sedes.region`/`sedes.comuna` son **snapshots del ETL** (denormalizados); se sobreescriben en cada recarga, no se sincronizan con las tablas de referencia.

## Reporte (`report.json`)

- **Bug histórico corregido**: el `report.json` generado por `run_etl.py` mezclaba el *delta* de la última corrida (`comunas_exitosas: 11`) con el *total* acumulado (`filas_por_tabla.establecimientos: 7673`), lo que hizo concluir erróneamente "dataset incompleto". 
- `run_etl.py` ahora separa campos delta (`*_delta`) y acumulados (`comunas_en_dataset`, `rbds_en_dataset`).
- `scripts/validate_dataset.py` regenera el reporte con la cobertura real **sin tocar la red**.

## Calidad

- Integridad referencial limpia: 0 sedes huérfanas, 0 cursos sin sede, 0 RBDs duplicados, 0 establecimientos sin sedes.
- 0 nulls en claves primarias (`rbd`, `nombre`, `codigo_sede`).

## Naming en el mapeo de comunas

- `assets/comunas_mapeo.json` contiene variantes/typos de nombres: `MARCHIGUE`→`MARCHIHUE`, `ANTARTIDA`→`ANTARTICA`, `EST CENTRAL`→`ESTACION CENTRAL`. El script de validación normaliza (tildes, espacios, guiones, apóstrofes) antes de comparar.
