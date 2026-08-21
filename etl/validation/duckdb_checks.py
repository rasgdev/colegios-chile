import datetime
from pathlib import Path

import duckdb
import structlog

logger = structlog.get_logger()

QUERIES = {
    "sedes_huerfanas": """
        SELECT s.rbd
        FROM read_parquet('{dir}/sedes.parquet') s
        LEFT JOIN read_parquet('{dir}/establecimientos.parquet') e ON s.rbd = e.rbd
        WHERE e.rbd IS NULL
    """,
    "cursos_sin_sede": """
        SELECT c.rbd, c.codigo_sede
        FROM read_parquet('{dir}/cursos.parquet') c
        LEFT JOIN read_parquet('{dir}/sedes.parquet') s
          ON c.rbd = s.rbd AND c.codigo_sede = s.codigo_sede
        WHERE s.rbd IS NULL
    """,
    "rbds_duplicados": """
        SELECT rbd, COUNT(*) AS n
        FROM read_parquet('{dir}/establecimientos.parquet')
        GROUP BY rbd
        HAVING n > 1
    """,
    "establecimientos_sin_sedes": """
        SELECT e.rbd
        FROM read_parquet('{dir}/establecimientos.parquet') e
        LEFT JOIN read_parquet('{dir}/sedes.parquet') s ON e.rbd = s.rbd
        WHERE s.rbd IS NULL
    """,
    "nulos_en_claves_establecimientos": """
        SELECT COUNT(*) AS nulos
        FROM read_parquet('{dir}/establecimientos.parquet')
        WHERE rbd IS NULL OR nombre IS NULL
    """,
    "nulos_en_claves_sedes": """
        SELECT COUNT(*) AS nulos
        FROM read_parquet('{dir}/sedes.parquet')
        WHERE rbd IS NULL OR codigo_sede IS NULL
    """,
}


def validar(data_dir: str | None = None) -> dict[str, int]:
    if data_dir is None:
        hoy = datetime.date.today().isoformat()
        data_dir = f"data/processed/{hoy}"

    path = Path(data_dir)
    if not path.exists():
        logger.error("directorio_no_existe", dir=str(path))
        return {}

    con = duckdb.connect(":memory:")
    resultados: dict[str, int] = {}

    for nombre, query in QUERIES.items():
        try:
            result = con.execute(query.format(dir=data_dir)).fetchall()
            count = len(result)
            resultados[nombre] = count

            if count > 0:
                logger.warning("validacion_fallida", check=nombre, count=count)
            else:
                logger.info("validacion_ok", check=nombre)

        except Exception:
            logger.exception("error_validacion", check=nombre)
            resultados[nombre] = -1

    con.close()

    total_fallas = sum(1 for v in resultados.values() if v > 0)
    logger.info("validacion_completada", checks=len(resultados), fallas=total_fallas)

    return resultados


if __name__ == "__main__":
    import json

    results = validar()
    print(json.dumps(results, indent=2))
