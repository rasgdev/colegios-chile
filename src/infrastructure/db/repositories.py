"""Implementaciones SQLAlchemy async de los Protocols de dominio."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import (
    Actividad,
    Comuna,
    Curso,
    CursoResumen,
    Establecimiento,
    Imagen,
    Indicador,
    Region,
    Sede,
)
from src.infrastructure.db import orm


# ── Mapeo ORM → entidad de dominio ────────────────────────────────────────────


def _to_region(row: orm.Region) -> Region:
    return Region(codigo=row.codigo, nombre=row.nombre)


def _to_comuna(row: orm.Comuna) -> Comuna:
    return Comuna(codigo=row.codigo, nombre=row.nombre, codigo_region=row.codigo_region)


def _to_establecimiento(row: orm.Establecimiento) -> Establecimiento:
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
    )


def _to_sede(row: orm.Sede) -> Sede:
    return Sede(
        rbd=row.rbd,
        codigo_sede=row.codigo_sede,
        codigo_region=row.codigo_region,
        codigo_comuna=row.codigo_comuna,
        region=row.region,
        comuna=row.comuna,
        calle=row.calle,
        latitud=row.latitud,
        longitud=row.longitud,
    )


def _to_curso(row: orm.Curso) -> Curso:
    return Curso(
        rbd=row.rbd,
        codigo_curso=row.codigo_curso,
        codigo_sede=row.codigo_sede,
        glosa_grupo_ensenanza=row.glosa_grupo_ensenanza,
        glosa_ensenanza=row.glosa_ensenanza,
        glosa_nivel=row.glosa_nivel,
        etiqueta_nivel=row.etiqueta_nivel,
        sexo=row.sexo,
        glosa_jornada=row.glosa_jornada,
        glosa_especialidad=row.glosa_especialidad,
        glosa_grupo_pago=row.glosa_grupo_pago,
        codigo_ensenanza=row.codigo_ensenanza,
        codigo_nivel=row.codigo_nivel,
        codigo_jornada=row.codigo_jornada,
        codigo_sexo=row.codigo_sexo,
        codigo_especialidad=row.codigo_especialidad,
        unico_comuna=row.unico_comuna,
        proporcion_excelencia_transicion=row.proporcion_excelencia_transicion,
        proporcion_excelencia_regimen=row.proporcion_excelencia_regimen,
        proporcion_especializacion_temprana=row.proporcion_especializacion_temprana,
        copago_cuotas=row.copago_cuotas,
        copago_valor=row.copago_valor,
        cupos_totales=row.cupos_totales,
        vacantes_rango_inferior=row.vacantes_rango_inferior,
        vacantes_rango_superior=row.vacantes_rango_superior,
        porcentaje_cambio_inferior=row.porcentaje_cambio_inferior,
        porcentaje_cambio_superior=row.porcentaje_cambio_superior,
        repitentes_anio_actual=row.repitentes_anio_actual,
        repitentes_nivel_anterior=row.repitentes_nivel_anterior,
        pre_inscritos_anio_siguiente=row.pre_inscritos_anio_siguiente,
        cambios_inferior=row.cambios_inferior,
        cambios_superior=row.cambios_superior,
        pre_vacantes_inferior=row.pre_vacantes_inferior,
        pre_vacantes_superior=row.pre_vacantes_superior,
        rango=row.rango,
        postulantes_anio_anterior=row.postulantes_anio_anterior,
        movimiento_lista_espera_anterior=row.movimiento_lista_espera_anterior,
    )


def _to_curso_resumen(row: orm.Curso) -> CursoResumen:
    return CursoResumen(
        codigo_curso=row.codigo_curso,
        glosa_nivel=row.glosa_nivel,
        etiqueta_nivel=row.etiqueta_nivel,
        sexo=row.sexo,
        glosa_jornada=row.glosa_jornada,
        copago_cuotas=row.copago_cuotas,
        copago_valor=row.copago_valor,
        cupos_totales=row.cupos_totales,
    )


def _to_indicador(row: orm.Indicador) -> Indicador:
    return Indicador(
        id=row.id,
        rbd=row.rbd,
        tipo_indicador=row.tipo_indicador,
        titulo_indicador=row.titulo_indicador,
        nivel_indicador=row.nivel_indicador,
        descripcion_indicador=row.descripcion_indicador,
        nombre_indicador=row.nombre_indicador,
        puntaje=row.puntaje,
        comparacion_gse_numero=row.comparacion_gse_numero,
        comparacion_gse_glosa=row.comparacion_gse_glosa,
    )


def _to_actividad(row: orm.Actividad) -> Actividad:
    return Actividad(
        id=row.id,
        rbd=row.rbd,
        tipo=row.tipo,
        nombre=row.nombre,
        nivel=row.nivel,
        exigencia=row.exigencia,
    )


def _to_imagen(row: orm.Imagen) -> Imagen:
    return Imagen(
        id=row.id,
        rbd=row.rbd,
        nombre=row.nombre,
        url=row.url,
        principal=row.principal,
    )


# ── Repositorios ──────────────────────────────────────────────────────────────


class SqlRegionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Region]:
        rows = (await self.session.execute(select(orm.Region).order_by(orm.Region.codigo))).scalars().all()
        return [_to_region(r) for r in rows]


class SqlComunaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Comuna]:
        rows = (await self.session.execute(select(orm.Comuna).order_by(orm.Comuna.codigo))).scalars().all()
        return [_to_comuna(r) for r in rows]

    async def list_by_region(self, codigo_region: int) -> list[Comuna]:
        rows = (
            await self.session.execute(
                select(orm.Comuna)
                .where(orm.Comuna.codigo_region == codigo_region)
                .order_by(orm.Comuna.nombre)
            )
        ).scalars().all()
        return [_to_comuna(r) for r in rows]


class SqlEstablecimientoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_rbd(self, rbd: int) -> Establecimiento | None:
        row = await self.session.get(orm.Establecimiento, rbd)
        return _to_establecimiento(row) if row else None

    async def get_many(self, rbds: list[int]) -> list[Establecimiento]:
        rows = (
            (await self.session.execute(select(orm.Establecimiento).where(orm.Establecimiento.rbd.in_(rbds))))
            .scalars()
            .all()
        )
        return [_to_establecimiento(r) for r in rows]

    async def exists(self, rbd: int) -> bool:
        n = (
            await self.session.execute(
                select(func.count()).select_from(orm.Establecimiento).where(orm.Establecimiento.rbd == rbd)
            )
        ).scalar_one()
        return n > 0

    async def list_paginated(
        self,
        limit: int,
        offset: int,
        *,
        dependencia: str | None = None,
        regimen: str | None = None,
    ) -> tuple[list[Establecimiento], int]:
        conditions = []
        if dependencia is not None:
            conditions.append(orm.Establecimiento.dependencia == dependencia)
        if regimen is not None:
            conditions.append(func.upper(orm.Establecimiento.regimen) == regimen)

        base = select(orm.Establecimiento)
        if conditions:
            base = base.where(*conditions)

        total = (
            await self.session.execute(
                select(func.count()).select_from(orm.Establecimiento).where(*conditions)
                if conditions
                else select(func.count()).select_from(orm.Establecimiento)
            )
        ).scalar_one()

        rows = (
            await self.session.execute(
                base.order_by(orm.Establecimiento.nombre).limit(limit).offset(offset)
            )
        ).scalars().all()
        return [_to_establecimiento(r) for r in rows], total

    async def total(self) -> int:
        return (
            await self.session.execute(select(func.count()).select_from(orm.Establecimiento))
        ).scalar_one()


class SqlSedeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_rbd(self, rbd: int) -> list[Sede]:
        rows = (
            await self.session.execute(
                select(orm.Sede).where(orm.Sede.rbd == rbd).order_by(orm.Sede.codigo_sede)
            )
        ).scalars().all()
        return [_to_sede(r) for r in rows]


class SqlCursoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_rbd(self, rbd: int) -> list[Curso]:
        rows = (
            await self.session.execute(
                select(orm.Curso).where(orm.Curso.rbd == rbd).order_by(orm.Curso.codigo_curso)
            )
        ).scalars().all()
        return [_to_curso(r) for r in rows]

    async def resumen_by_rbd(self, rbd: int) -> list[CursoResumen]:
        rows = (
            await self.session.execute(
                select(orm.Curso).where(orm.Curso.rbd == rbd).order_by(orm.Curso.codigo_curso)
            )
        ).scalars().all()
        return [_to_curso_resumen(r) for r in rows]


class SqlIndicadorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_rbd(self, rbd: int) -> list[Indicador]:
        rows = (
            await self.session.execute(
                select(orm.Indicador).where(orm.Indicador.rbd == rbd).order_by(orm.Indicador.id)
            )
        ).scalars().all()
        return [_to_indicador(r) for r in rows]

    async def by_rbds(self, rbds: list[int]) -> list[Indicador]:
        rows = (
            await self.session.execute(
                select(orm.Indicador)
                .where(orm.Indicador.rbd.in_(rbds))
                .order_by(orm.Indicador.rbd, orm.Indicador.id)
            )
        ).scalars().all()
        return [_to_indicador(r) for r in rows]


class SqlActividadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_rbd(self, rbd: int) -> list[Actividad]:
        rows = (
            await self.session.execute(
                select(orm.Actividad).where(orm.Actividad.rbd == rbd).order_by(orm.Actividad.id)
            )
        ).scalars().all()
        return [_to_actividad(r) for r in rows]


class SqlImagenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_rbd(self, rbd: int) -> list[Imagen]:
        rows = (
            await self.session.execute(
                select(orm.Imagen).where(orm.Imagen.rbd == rbd).order_by(orm.Imagen.id)
            )
        ).scalars().all()
        return [_to_imagen(r) for r in rows]
