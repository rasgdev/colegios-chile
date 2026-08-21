import asyncio
import datetime
import json
import sys
import time
from pathlib import Path

# Asegura que los paquetes de ESTE repo (etl/, config/) ganen la resolución
# de imports al ejecutar el script directamente (sin `make`/PYTHONPATH).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import structlog

from config.logging import configure

from config.settings import settings
from etl.api_client.client import APIClient
from etl.extract.comunas import cargar_mapeo_comunas
from etl.extract.detalle import extraer_comuna, extraer_rbds
from etl.load.parquet import guardar_parquets
from etl.state import ETLState
from etl.transform.normalizers import transformar_todo
from etl.validation.duckdb_checks import validar

logger = structlog.get_logger()


class ETLReport:
    def __init__(self) -> None:
        self.start_time = time.monotonic()
        self.fecha_ejecucion = ""
        self.version_dataset = ""
        # Cobertura acumulada del dataset resultante (independiente de la corrida)
        self.comunas_totales = 0
        self.comunas_en_dataset = 0
        self.rbds_en_dataset = 0
        # Delta de la corrida actual (qué se descargó/falló esta vez)
        self.comunas_procesadas_delta = 0
        self.comunas_fallidas_delta = 0
        self.rbds_descargados_delta = 0
        self.rbds_exitosos_delta = 0
        self.rbds_fallidos_delta = 0
        self.filas_por_tabla: dict[str, int] = {}
        self.validaciones: dict[str, int] = {}

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.start_time

    def to_dict(self) -> dict:
        return {
            "fecha_ejecucion": self.fecha_ejecucion,
            "version_dataset": self.version_dataset,
            "execution_time_seconds": round(self.elapsed_seconds, 1),
            "comunas_totales": self.comunas_totales,
            "comunas_en_dataset": self.comunas_en_dataset,
            "rbds_en_dataset": self.rbds_en_dataset,
            "comunas_procesadas_delta": self.comunas_procesadas_delta,
            "comunas_fallidas_delta": self.comunas_fallidas_delta,
            "rbds_descargados_delta": self.rbds_descargados_delta,
            "rbds_exitosos_delta": self.rbds_exitosos_delta,
            "rbds_fallidos_delta": self.rbds_fallidos_delta,
            "filas_por_tabla": self.filas_por_tabla,
            "validaciones": self.validaciones,
        }

    def guardar(self, output_dir: str) -> None:
        import os

        os.makedirs(output_dir, exist_ok=True)
        path = f"{output_dir}/report.json"
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


async def _extraer(report: ETLReport) -> None:
    mapeo = cargar_mapeo_comunas()
    comunas_a_procesar = list(mapeo.values())
    report.comunas_totales = len(comunas_a_procesar)

    state = ETLState.cargar()

    client = APIClient()
    try:
        for comuna in comunas_a_procesar:
            if state.comuna_esta_procesada(comuna):
                logger.debug("comuna_ya_procesada", comuna=comuna)
                continue

            try:
                rbds = await extraer_comuna(client, comuna, state)
                report.comunas_procesadas_delta += 1

                e, f = await extraer_rbds(client, rbds, state)
                report.rbds_exitosos_delta += e
                report.rbds_fallidos_delta += f
                report.rbds_descargados_delta += len(rbds)

            except Exception:
                logger.exception("comuna_fallida", comuna=comuna)
                report.comunas_fallidas_delta += 1

    finally:
        await client.close()


def _transformar_y_cargar(report: ETLReport) -> str:
    logger.info("iniciando_transformacion")

    dfs = transformar_todo()
    report.filas_por_tabla = {nombre: len(df) for nombre, df in dfs.items()}

    hoy = datetime.date.today().isoformat()
    output_dir = str(settings.processed_dir / hoy)
    guardar_parquets(dfs)

    # Cobertura acumulada del dataset resultante (no el delta de esta corrida)
    if "sedes" in dfs and "codigo_comuna" in dfs["sedes"].columns:
        report.comunas_en_dataset = int(dfs["sedes"]["codigo_comuna"].n_unique())
    if "establecimientos" in dfs:
        report.rbds_en_dataset = int(dfs["establecimientos"].height)

    report.fecha_ejecucion = datetime.datetime.now().isoformat()
    report.version_dataset = hoy

    logger.info("transformacion_completada", filas=report.filas_por_tabla)
    return output_dir


def _validar(output_dir: str, report: ETLReport) -> None:
    logger.info("iniciando_validacion")
    report.validaciones = validar(output_dir)


async def main() -> None:
    configure()
    settings.raw_dir.mkdir(parents=True, exist_ok=True)

    report = ETLReport()

    logger.info("etl_iniciado", paso="extraccion")
    await _extraer(report)

    logger.info("etl_iniciado", paso="transformacion")
    output_dir = _transformar_y_cargar(report)

    logger.info("etl_iniciado", paso="validacion")
    _validar(output_dir, report)

    report.guardar(output_dir)

    logger.info("etl_completado", **report.to_dict())
    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
