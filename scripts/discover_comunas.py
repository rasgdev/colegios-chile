import asyncio
import sys
from pathlib import Path

# Asegura que los paquetes de ESTE repo (etl/, config/) ganen la resolución
# de imports al ejecutar el script directamente (sin `make`/PYTHONPATH).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.logging import configure
from etl.api_client.client import APIClient
from etl.extract.comunas import discover_comunas


async def main() -> None:
    configure()
    client = APIClient()
    try:
        mapeo = await discover_comunas(client)
        print(f"\nMapeo generado: {len(mapeo)} comunas → assets/comunas_mapeo.json")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
