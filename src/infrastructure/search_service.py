"""Full-Text Search con `tsvector` + `unaccent` (SQL crudo).

Acoplado al motor de búsqueda de PostgreSQL a propósito: un Repository genérico
sería una falsa abstracción (decisión #7 de ARCHITECTURE_v2). Si se migrara a
Elasticsearch, se reemplazaría este servicio, no los repositorios.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import (
    NIVEL_ORDEN,
    Establecimiento,
    SearchPage,
    SearchQuery,
    rango_indices_categoria,
)

# Columnas de `establecimientos` a seleccionar (sin `busqueda_tsvector` generado).
_EST_COLUMNS = (
    "rbd", "nombre", "dependencia", "telefono", "mail", "url",
    "habilitado_postular", "publicado", "nivel_minimo", "nivel_maximo",
    "director", "etiquetas", "resumen_proyecto", "documento_proyecto",
    "documento_reglamento", "internado", "integracion", "subvencion_preferencial",
    "peib", "politica_uniforme", "orientacion_religiosa", "alumnos_matriculados",
    "promedio_alumnos_por_curso", "cantidad_docentes", "regimen",
)

_RANK_EXPR = "ts_rank_cd(busqueda_tsvector, websearch_to_tsquery('spanish_unaccent', :q))"

# Subqueries correlacionadas para ubicación (primera sede por codigo_sede).
_UBICACION_SQL = (
    "(SELECT s.comuna FROM sedes s WHERE s.rbd = establecimientos.rbd "
    "ORDER BY s.codigo_sede LIMIT 1) AS comuna, "
    "(SELECT s.region FROM sedes s WHERE s.rbd = establecimientos.rbd "
    "ORDER BY s.codigo_sede LIMIT 1) AS region"
)


def _nivel_case(column: str) -> str:
    """CASE que mapea un grado concreto a su índice ordinal (para rango de nivel)."""
    cases = " ".join(f"WHEN '{grado}' THEN {i}" for grado, i in NIVEL_ORDEN.items())
    return f"CASE {column} {cases} ELSE NULL END"


def _row_to_establecimiento(row) -> Establecimiento:
    return Establecimiento(
        rbd=row.rbd,
        nombre=row.nombre,
        dependencia=row.dependencia,
        telefono=row.telefono,
        mail=row.mail,
        url=row.url,
        habilitado_postular=row.habilitado_postular,
        publicado=row.publicado,
        nivel_minimo=row.nivel_minimo,
        nivel_maximo=row.nivel_maximo,
        director=row.director,
        etiquetas=list(row.etiquetas or []),
        resumen_proyecto=row.resumen_proyecto,
        documento_proyecto=row.documento_proyecto,
        documento_reglamento=row.documento_reglamento,
        internado=row.internado,
        integracion=row.integracion,
        subvencion_preferencial=row.subvencion_preferencial,
        peib=row.peib,
        politica_uniforme=row.politica_uniforme,
        orientacion_religiosa=row.orientacion_religiosa,
        alumnos_matriculados=row.alumnos_matriculados,
        promedio_alumnos_por_curso=row.promedio_alumnos_por_curso,
        cantidad_docentes=row.cantidad_docentes,
        regimen=row.regimen,
        comuna=row.comuna,
        region=row.region,
    )


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, query: SearchQuery) -> SearchPage:
        where, params, has_q = self._build_where(query)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        # Conteo total (sin paginación).
        total = (
            await self.session.execute(
                text(f"SELECT count(*) FROM establecimientos {where_sql}"), params
            )
        ).scalar_one()

        order = (
            f"{_RANK_EXPR} DESC, nombre ASC"
            if has_q
            else "nombre ASC"
        )
        cols = ", ".join(_EST_COLUMNS)
        sql = (
            f"SELECT {cols}, {_UBICACION_SQL} FROM establecimientos {where_sql} "
            f"ORDER BY {order} LIMIT :limit OFFSET :offset"
        )
        params = {**params, "limit": query.limit, "offset": query.offset}

        result = await self.session.execute(text(sql), params)
        items = [_row_to_establecimiento(r) for r in result.mappings().all()]

        return SearchPage(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )

    def _build_where(self, query: SearchQuery) -> tuple[list[str], dict, bool]:
        where: list[str] = []
        params: dict = {}
        q = query.q.strip() if query.q else ""
        has_q = bool(q)

        if has_q:
            where.append(
                "busqueda_tsvector @@ websearch_to_tsquery('spanish_unaccent', :q)"
            )
            params["q"] = q

        if query.dependencia:
            where.append("dependencia = :dependencia")
            params["dependencia"] = query.dependencia

        if query.regimen:
            where.append("UPPER(regimen) = :regimen")
            params["regimen"] = query.regimen

        if query.etiquetas:
            where.append("etiquetas @> :etiquetas")
            params["etiquetas"] = query.etiquetas

        if query.copago_max is not None:
            where.append(
                "EXISTS (SELECT 1 FROM cursos c "
                "WHERE c.rbd = establecimientos.rbd AND c.copago_valor <= :copago_max)"
            )
            params["copago_max"] = query.copago_max

        if query.comuna:
            where.append(
                "EXISTS (SELECT 1 FROM sedes s "
                "WHERE s.rbd = establecimientos.rbd AND s.comuna ILIKE :comuna)"
            )
            params["comuna"] = f"%{query.comuna}%"

        if query.region is not None:
            where.append(
                "EXISTS (SELECT 1 FROM sedes s "
                "WHERE s.rbd = establecimientos.rbd AND s.codigo_region = :region)"
            )
            params["region"] = query.region

        if query.nivel:
            cat_min, cat_max = rango_indices_categoria(query.nivel)
            where.append(
                f"({_nivel_case('nivel_minimo')} <= :nivel_max_idx "
                f"AND {_nivel_case('nivel_maximo')} >= :nivel_min_idx)"
            )
            params["nivel_max_idx"] = cat_max
            params["nivel_min_idx"] = cat_min

        return where, params, has_q
