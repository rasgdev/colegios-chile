import json
import re
import unicodedata

import httpx
import structlog
from tqdm.asyncio import tqdm_asyncio

from config.settings import settings
from etl.api_client.client import APIClient

logger = structlog.get_logger()

PREFIXES_TO_STRIP = ["PUERTO "]
ARTICLES = ["DE", "LA", "LAS", "LOS", "DEL"]


def _remover_tildes(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_comuna(nombre: str) -> str:
    nombre = nombre.upper().strip()
    nombre = _remover_tildes(nombre)
    nombre = nombre.replace("'", "")
    nombre = re.sub(r"\s+", "_", nombre)
    nombre = nombre.replace("-", "")

    partes = nombre.split("_")
    resultado: list[str] = []
    i = 0
    while i < len(partes):
        if i + 1 < len(partes) and partes[i] == partes[i + 1]:
            resultado.append(partes[i] + partes[i + 1])
            i += 2
        else:
            resultado.append(partes[i])
            i += 1

    return "_".join(resultado)


def generar_variantes(nombre: str) -> list[str]:
    variantes = [nombre]
    partes = nombre.split("_")

    for prefijo in PREFIXES_TO_STRIP:
        for candidate in (prefijo, prefijo.replace(" ", "_")):
            if nombre.startswith(candidate):
                variantes.append(nombre[len(candidate):])

    for articulo in ARTICLES:
        if articulo in partes:
            sin_articulo = "_".join(p for p in partes if p != articulo)
            variantes.append(sin_articulo)

    return list(dict.fromkeys(variantes))


async def probar_comuna(client: APIClient, nombre: str) -> bool:
    try:
        await client.get_establecimientos_por_comuna(nombre)
        return True
    except Exception:
        return False


async def fetch_comunas_raw() -> list[str]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(settings.comunas_api_url)
        response.raise_for_status()
        data = response.json()
        return data["data"]["comunas"]


async def discover_comunas(client: APIClient) -> dict[str, str]:
    nombres_raw = await fetch_comunas_raw()

    mapeo: dict[str, str] = {}

    async def _probar_y_mapear(nombre_raw: str) -> None:
        normalizado = normalizar_comuna(nombre_raw)
        if await probar_comuna(client, normalizado):
            mapeo[nombre_raw] = normalizado
            return

        for variante in generar_variantes(normalizado):
            if variante == normalizado:
                continue
            if await probar_comuna(client, variante):
                mapeo[nombre_raw] = variante
                logger.info("comuna_variante_encontrada", raw=nombre_raw, variant=variante)
                return

        logger.warning("comuna_sin_match", nombre_raw=nombre_raw)
        mapeo[nombre_raw] = normalizado

    await tqdm_asyncio.gather(
        *[_probar_y_mapear(n) for n in nombres_raw],
        desc="Probing comunas",
    )

    settings.comunas_mapeo_file.parent.mkdir(parents=True, exist_ok=True)
    settings.comunas_mapeo_file.write_text(
        json.dumps(mapeo, indent=2, ensure_ascii=False)
    )

    logger.info("discovery_completado", total=len(mapeo), matches=sum(1 for v in mapeo.values() if v))

    return mapeo


def cargar_mapeo_comunas() -> dict[str, str]:
    if not settings.comunas_mapeo_file.exists():
        raise FileNotFoundError(
            f"Mapping file not found: {settings.comunas_mapeo_file}. Run discover_comunas first."
        )
    return json.loads(settings.comunas_mapeo_file.read_text())
