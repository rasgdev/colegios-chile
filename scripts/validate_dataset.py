"""Valida el dataset existente (Parquet) sin tocar la red.

Regenera `report.json` con la cobertura acumulada real, corrigiendo el bug
histórico donde el reporte mezclaba el *delta* de la última corrida con el
*total* del dataset (ver `docs/KNOWN_ISSUES.md`).

Uso:
    python3 scripts/validate_dataset.py [--data-dir data/processed/latest]
"""

import argparse
import datetime
import json
import re
import unicodedata
from pathlib import Path

import polars as pl

TABLAS = [
    "establecimientos",
    "sedes",
    "cursos",
    "actividades",
    "indicadores",
    "imagenes",
]


def _norm(s: str) -> str:
    s = s.upper()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]", "", s)


def _cargar_mapeo(mapeo_file: Path) -> dict[str, str]:
    with open(mapeo_file) as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/processed/latest")
    parser.add_argument("--mapeo", default="assets/comunas_mapeo.json")
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    version_dataset = data_dir.name
    mapeo = _cargar_mapeo(Path(args.mapeo))

    filas_por_tabla: dict[str, int] = {}
    dfs: dict[str, pl.DataFrame] = {}
    for tabla in TABLAS:
        path = data_dir / f"{tabla}.parquet"
        if not path.exists():
            continue
        df = pl.read_parquet(path)
        dfs[tabla] = df
        filas_por_tabla[tabla] = df.height

    sedes = dfs.get("sedes")
    establecimientos = dfs.get("establecimientos")

    comunas_en_dataset = int(sedes["codigo_comuna"].n_unique()) if sedes is not None else 0
    regiones_en_dataset = int(sedes["codigo_region"].n_unique()) if sedes is not None else 0
    rbds_en_dataset = establecimientos.height if establecimientos is not None else 0

    if sedes is not None:
        presentes = {_norm(x) for x in sedes["comuna"].to_list()}
        comunas_faltantes = sorted(v for v in mapeo.values() if _norm(v) not in presentes)
    else:
        comunas_faltantes = []

    validaciones: dict[str, int] = {}
    if establecimientos is not None:
        validaciones["nulos_en_claves_establecimientos"] = int(
            establecimientos.filter(pl.col("rbd").is_null() | pl.col("nombre").is_null()).height
        )
    if sedes is not None:
        validaciones["nulos_en_claves_sedes"] = int(
            sedes.filter(pl.col("rbd").is_null() | pl.col("codigo_sede").is_null()).height
        )

    report = {
        "fecha_ejecucion": datetime.datetime.now().isoformat(),
        "version_dataset": version_dataset,
        "comunas_totales": len(mapeo),
        "comunas_en_dataset": comunas_en_dataset,
        "regiones_en_dataset": regiones_en_dataset,
        "rbds_en_dataset": rbds_en_dataset,
        "comunas_faltantes": comunas_faltantes,
        "filas_por_tabla": filas_por_tabla,
        "validaciones": validaciones,
    }

    out = data_dir / "report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
