"""Loader atómico: Parquet → PostgreSQL (staging + swap transaccional).

Estrategia (Opción A del roadmap, decisión #14 de v2):

1. Crear tablas `*_staging` con `LIKE` (misma forma que las tablas finales, sin
   constraints salvo NOT NULL). Se recrean en cada carga.
2. Insertar datos desde Parquet a staging (SQLAlchemy Core async, chunked).
3. Validar staging: conteos, nulos en claves e integridad referencial.
4. Swap transaccional: `TRUNCATE` de las tablas finales + `INSERT ... SELECT`
   desde staging, todo en una única transacción.

Idempotente: reejecutar produce los mismos conteos. Interrumpir a mitad de carga
no deja la base inconsistente (el swap es una transacción).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import polars as pl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config.settings import settings

log = logging.getLogger(__name__)

CHUNK_SIZE = 2_000

# Columnas insertables (sin `busqueda_tsvector` generado ni `id` identity).
ESTABLECIMIENTOS_COLS = [
    "rbd", "nombre", "dependencia", "telefono", "mail", "url",
    "habilitado_postular", "publicado", "nivel_minimo", "nivel_maximo",
    "director", "etiquetas", "resumen_proyecto", "documento_proyecto",
    "documento_reglamento", "internado", "integracion", "subvencion_preferencial",
    "peib", "politica_uniforme", "orientacion_religiosa", "alumnos_matriculados",
    "promedio_alumnos_por_curso", "cantidad_docentes", "regimen",
]

SEDES_COLS = [
    "rbd", "codigo_sede", "codigo_region", "codigo_comuna", "region", "comuna",
    "calle", "latitud", "longitud",
]

CURSOS_COLS = [
    "rbd", "codigo_curso", "codigo_sede", "glosa_grupo_ensenanza", "glosa_ensenanza",
    "glosa_nivel", "etiqueta_nivel", "sexo", "glosa_jornada", "glosa_especialidad",
    "glosa_grupo_pago", "codigo_ensenanza", "codigo_nivel", "codigo_jornada",
    "codigo_sexo", "codigo_especialidad", "unico_comuna",
    "proporcion_excelencia_transicion", "proporcion_excelencia_regimen",
    "proporcion_especializacion_temprana", "copago_cuotas", "copago_valor",
    "cupos_totales", "vacantes_rango_inferior", "vacantes_rango_superior",
    "porcentaje_cambio_inferior", "porcentaje_cambio_superior",
    "repitentes_anio_actual", "repitentes_nivel_anterior",
    "pre_inscritos_anio_siguiente", "cambios_inferior", "cambios_superior",
    "pre_vacantes_inferior", "pre_vacantes_superior", "rango",
    "postulantes_anio_anterior", "movimiento_lista_espera_anterior",
]

INDICADORES_COLS = [
    "rbd", "tipo_indicador", "titulo_indicador", "nivel_indicador",
    "descripcion_indicador", "nombre_indicador", "puntaje",
    "comparacion_gse_numero", "comparacion_gse_glosa",
]

ACTIVIDADES_COLS = ["rbd", "tipo", "nombre", "nivel", "exigencia"]

IMAGENES_COLS = ["rbd", "nombre", "url", "principal"]

REGIONES_COLS = ["codigo", "nombre"]
COMUNAS_COLS = ["codigo", "nombre", "codigo_region"]

# Orden de carga por dependencias de FK.
PARQUET_TABLES = ["establecimientos", "sedes", "cursos", "indicadores", "actividades", "imagenes"]


@dataclass
class LoadSummary:
    """Conteos finales de la carga (para reporte/CLI)."""

    regiones: int = 0
    comunas: int = 0
    establecimientos: int = 0
    sedes: int = 0
    cursos: int = 0
    indicadores: int = 0
    actividades: int = 0
    imagenes: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "regiones": self.regiones,
            "comunas": self.comunas,
            "establecimientos": self.establecimientos,
            "sedes": self.sedes,
            "cursos": self.cursos,
            "indicadores": self.indicadores,
            "actividades": self.actividades,
            "imagenes": self.imagenes,
        }


class LoaderError(RuntimeError):
    pass


def _chunks(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def _transform_establecimientos(df: pl.DataFrame) -> pl.DataFrame:
    """Renombra habilitado_vitrina → publicado, convierte etiquetas CSV → list[str]."""
    df = df.rename({"habilitado_vitrina": "publicado"})
    df = df.select(ESTABLECIMIENTOS_COLS)
    df = df.with_columns(
        pl.col("etiquetas").map_elements(
            lambda v: v.split(",") if v else [],
            return_dtype=pl.List(pl.String),
        )
    )
    return df


def _derive_regiones_comunas(sedes: pl.DataFrame) -> tuple[list[dict], list[dict]]:
    regiones = (
        sedes.select(["codigo_region", "region"])
        .unique()
        .rename({"codigo_region": "codigo", "region": "nombre"})
        .sort("codigo")
    )
    comunas = (
        sedes.select(["codigo_comuna", "comuna", "codigo_region"])
        .unique()
        .rename({"codigo_comuna": "codigo", "comuna": "nombre"})
        .sort("codigo")
    )
    return regiones.to_dicts(), comunas.to_dicts()


class ParquetLoader:
    def __init__(self, engine: AsyncEngine, processed_dir: Path):
        self.engine = engine
        self.processed_dir = processed_dir
        self.summary = LoadSummary()

    async def load(self) -> LoadSummary:
        dfs = self._read_parquets()
        dfs["establecimientos"] = _transform_establecimientos(dfs["establecimientos"])
        regiones, comunas = _derive_regiones_comunas(dfs["sedes"])

        async with self.engine.begin() as conn:
            await self._truncate_staging(conn)
            await self._insert(conn, "regiones", REGIONES_COLS, regiones)
            await self._insert(conn, "comunas", COMUNAS_COLS, comunas)
            await self._insert(conn, "establecimientos", ESTABLECIMIENTOS_COLS, dfs["establecimientos"].to_dicts())
            await self._insert(conn, "sedes", SEDES_COLS, dfs["sedes"].select(SEDES_COLS).to_dicts())
            await self._insert(conn, "cursos", CURSOS_COLS, dfs["cursos"].select(CURSOS_COLS).to_dicts())
            await self._insert(conn, "indicadores", INDICADORES_COLS, dfs["indicadores"].select(INDICADORES_COLS).to_dicts())
            await self._insert(conn, "actividades", ACTIVIDADES_COLS, dfs["actividades"].select(ACTIVIDADES_COLS).to_dicts())
            await self._insert(conn, "imagenes", IMAGENES_COLS, dfs["imagenes"].with_columns(pl.lit(None).alias("url")).select(IMAGENES_COLS).to_dicts())

            await self._validate_staging(conn)
            await self._swap(conn)

        await self.engine.dispose()
        return self.summary

    def _read_parquets(self) -> dict[str, pl.DataFrame]:
        dfs: dict[str, pl.DataFrame] = {}
        for name in PARQUET_TABLES:
            path = self.processed_dir / f"{name}.parquet"
            if not path.exists():
                raise LoaderError(f"No se encontró {path}. Ejecuta el ETL primero (make etl).")
            dfs[name] = pl.read_parquet(path)
        return dfs

    async def _truncate_staging(self, conn) -> None:
        tables = ["regiones", "comunas"] + PARQUET_TABLES
        staging = ", ".join(f'"{t}_staging"' for t in tables)
        await conn.execute(text(f"TRUNCATE TABLE {staging}"))
        log.info("staging_truncated", tables=tables)

    async def _insert(self, conn, table: str, cols: list[str], rows: list[dict]) -> None:
        col_list = ", ".join(cols)
        placeholders = ", ".join(f":{c}" for c in cols)
        stmt = text(f'INSERT INTO "{table}_staging" ({col_list}) VALUES ({placeholders})')
        total = 0
        for chunk in _chunks(rows, CHUNK_SIZE):
            await conn.execute(stmt, chunk)
            total += len(chunk)
        log.info("staging_inserted", table=table, rows=total)

    async def _validate_staging(self, conn) -> None:
        checks: dict[str, str] = {
            "regiones_nulls": "SELECT count(*) FROM regiones_staging WHERE codigo IS NULL OR nombre IS NULL",
            "comunas_nulls": "SELECT count(*) FROM comunas_staging WHERE codigo IS NULL OR nombre IS NULL OR codigo_region IS NULL",
            "establecimientos_nulls": "SELECT count(*) FROM establecimientos_staging WHERE rbd IS NULL OR nombre IS NULL",
            "sedes_nulls": "SELECT count(*) FROM sedes_staging WHERE rbd IS NULL OR codigo_sede IS NULL",
            "cursos_nulls": "SELECT count(*) FROM cursos_staging WHERE rbd IS NULL OR codigo_curso IS NULL OR codigo_sede IS NULL",
            "sedes_huerfanas": (
                "SELECT count(*) FROM sedes_staging s "
                "LEFT JOIN establecimientos_staging e ON s.rbd = e.rbd WHERE e.rbd IS NULL"
            ),
            "cursos_sin_sede": (
                "SELECT count(*) FROM cursos_staging c "
                "LEFT JOIN sedes_staging s ON c.rbd = s.rbd AND c.codigo_sede = s.codigo_sede "
                "WHERE s.rbd IS NULL"
            ),
            "cursos_sin_est": (
                "SELECT count(*) FROM cursos_staging c "
                "LEFT JOIN establecimientos_staging e ON c.rbd = e.rbd WHERE e.rbd IS NULL"
            ),
        }

        failures = []
        for name, sql in checks.items():
            (n,) = (await conn.execute(text(sql))).fetchone()
            if n != 0:
                failures.append(f"{name}: {n} filas inválidas")

        # Conteos mínimos razonables.
        counts = {}
        for t in ["establecimientos", "sedes", "cursos"]:
            (n,) = (await conn.execute(text(f"SELECT count(*) FROM {t}_staging"))).fetchone()
            counts[t] = n

        if counts["establecimientos"] < 100:
            failures.append(f"establecimientos: solo {counts['establecimientos']} filas")
        if counts["sedes"] < 100:
            failures.append(f"sedes: solo {counts['sedes']} filas")

        if failures:
            raise LoaderError("Validación de staging falló: " + "; ".join(failures))

        log.info("staging_validated", counts=counts)

    async def _swap(self, conn) -> None:
        tables = ["regiones", "comunas"] + PARQUET_TABLES
        await conn.execute(text("TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"))

        insert_columns: dict[str, list[str]] = {
            "regiones": REGIONES_COLS,
            "comunas": COMUNAS_COLS,
            "establecimientos": ESTABLECIMIENTOS_COLS,
            "sedes": SEDES_COLS,
            "cursos": CURSOS_COLS,
            "indicadores": INDICADORES_COLS,
            "actividades": ACTIVIDADES_COLS,
            "imagenes": IMAGENES_COLS,
        }
        for t in tables:
            cols = insert_columns[t]
            col_list = ", ".join(cols)
            await conn.execute(
                text(f'INSERT INTO "{t}" ({col_list}) SELECT {col_list} FROM "{t}_staging"')
            )

        # Conteos finales para el summary.
        for t, attr in [
            ("regiones", "regiones"), ("comunas", "comunas"),
            ("establecimientos", "establecimientos"), ("sedes", "sedes"),
            ("cursos", "cursos"), ("indicadores", "indicadores"),
            ("actividades", "actividades"), ("imagenes", "imagenes"),
        ]:
            (n,) = (await conn.execute(text(f'SELECT count(*) FROM "{t}"'))).fetchone()
            setattr(self.summary, attr, n)

        log.info("swap_completed", counts=self.summary.as_dict())


async def load_parquets_to_db(processed_dir: Path | None = None) -> LoadSummary:
    """Entry point: carga los Parquet de `processed_dir` a PostgreSQL."""
    engine = create_async_engine(settings.database_url)
    loader = ParquetLoader(engine, processed_dir or settings.latest_processed_dir)
    return await loader.load()
