import datetime
import shutil
from pathlib import Path
from typing import Optional

import polars as pl
import structlog

logger = structlog.get_logger()


def guardar_parquets(
    dataframes: dict[str, pl.DataFrame],
    output_dir: Optional[Path] = None,
) -> Path:
    if output_dir is None:
        hoy = datetime.date.today().isoformat()
        output_dir = Path("data/processed") / hoy

    output_dir.mkdir(parents=True, exist_ok=True)

    filas_por_tabla: dict[str, int] = {}

    for nombre, df in dataframes.items():
        path = output_dir / f"{nombre}.parquet"
        df.write_parquet(path)
        filas_por_tabla[nombre] = len(df)
        logger.info("parquet_escrito", tabla=nombre, filas=len(df), path=str(path))

    latest_dir = Path("data/processed/latest")
    if latest_dir.is_symlink() or latest_dir.exists():
        if latest_dir.is_symlink():
            latest_dir.unlink()
        else:
            shutil.rmtree(latest_dir)
    latest_dir.symlink_to(output_dir.resolve(), target_is_directory=True)

    logger.info("parquets_guardados", output_dir=str(output_dir), filas=filas_por_tabla)
    return output_dir
