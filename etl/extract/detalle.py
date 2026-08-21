import json

import structlog
from tqdm.asyncio import tqdm_asyncio

from config.settings import settings
from etl.api_client.client import APIClient
from etl.state import ETLState

logger = structlog.get_logger()


async def extraer_comuna(
    client: APIClient, comuna: str, state: ETLState
) -> list[int]:
    path = settings.comunas_raw_dir / f"{comuna}.json"
    data = await client.get_establecimientos_por_comuna(comuna)
    settings.comunas_raw_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    rbds: list[int] = []
    for item in data:
        if "rbd" in item:
            rbds.append(item["rbd"])

    state.marcar_comuna(comuna)
    state.guardar()

    logger.info("comuna_extraida", comuna=comuna, rbds=len(rbds))
    return rbds


async def extraer_detalle(
    client: APIClient, rbd: int, state: ETLState
) -> bool:
    try:
        data = await client.get_detalle_establecimiento(rbd)
        path = settings.establecimientos_raw_dir / f"{rbd}.json"
        settings.establecimientos_raw_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        state.marcar_rbd(rbd)
        state.guardar()
        return True

    except Exception:
        logger.exception("rbd_fallido", rbd=rbd)
        state.marcar_rbd_fallido(rbd)
        return False


async def extraer_rbds(
    client: APIClient, rbds: list[int], state: ETLState
) -> tuple[int, int]:
    pendientes = [r for r in rbds if not state.rbd_esta_descargado(r)]
    if not pendientes:
        return 0, 0

    exitosos = 0
    fallidos = 0

    async def _worker(rbd: int) -> bool:
        return await extraer_detalle(client, rbd, state)

    results = await tqdm_asyncio.gather(
        *[_worker(r) for r in pendientes],
        desc=f"RBds ({len(pendientes)} pendientes)",
    )

    for ok in results:
        if ok:
            exitosos += 1
        else:
            fallidos += 1

    return exitosos, fallidos
