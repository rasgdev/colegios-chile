"""CLI: carga los Parquet procesados a PostgreSQL (staging + swap transaccional).

Uso:
    python scripts/load_to_db.py

Lee de `data/processed/latest/*.parquet` (configurable vía PROCESSED_DIR) y
ejecuta el loader atómico. Ver docs/DATA_LOADING.md.
"""

import asyncio
import sys
from pathlib import Path

# Asegura que los paquetes de ESTE repo (config/, src/) ganen la resolución de
# imports al ejecutar el script directamente (sin `make`/PYTHONPATH).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import settings
from src.infrastructure.loader import LoaderError, load_parquets_to_db


async def main() -> None:
    print(f"Origen: {settings.latest_processed_dir}")
    print(f"Destino: {settings.database_url.split('@')[-1]}")
    try:
        summary = await load_parquets_to_db()
    except LoaderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Carga completada:")
    for table, count in summary.as_dict().items():
        print(f"  {table:>16}: {count:,}")


if __name__ == "__main__":
    asyncio.run(main())
