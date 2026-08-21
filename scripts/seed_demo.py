"""Genera 50 colegios demo determinísticos para reviewers de portafolio.

Permite levantar la API con datos de prueba sin ejecutar el ETL completo.
Dos ejecuciones consecutivas producen exactamente la misma base (random.seed(42)).

Los RBDs demo usan el rango 990000+ para no colisionar con datos reales del
MINEDUC. Idempotente: borra los datos demo previos antes de insertar.

Uso:
    python scripts/seed_demo.py
"""
from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete

from src.infrastructure.db import orm
from src.infrastructure.db.session import async_session_factory

RBD_BASE = 990001
TOTAL = 50

DEPENDENCIAS = ["PUBLICO", "PARTICULAR SUBVENCIONADO", "SERVICIO LOCAL DE EDUCACIÓN"]
REGIMENES = ["Mixto", "Hombres", "Mujeres"]
ETIQUETAS = ["GRATUITO", "PIE", "SEP", "INTERNADO", "TECNICO_PROFESIONAL"]

NIVELES_POR_COLEGIO = [
    ("Pre-Kinder", "Kinder"),
    ("Pre-Kinder", "8º Básico"),
    ("1º Básico", "8º Básico"),
    ("7º Básico", "IV Medio"),
    ("Pre-Kinder", "IV Medio"),
]


def _build_establecimientos(rng: random.Random) -> list[orm.Establecimiento]:
    ests = []
    for i in range(TOTAL):
        rbd = RBD_BASE + i
        tags = rng.sample(ETIQUETAS, k=rng.randint(1, 3))
        nivel_min, nivel_max = NIVELES_POR_COLEGIO[i % len(NIVELES_POR_COLEGIO)]
        ests.append(
            orm.Establecimiento(
                rbd=rbd,
                nombre=f"Colegio Demo {i + 1}",
                dependencia=DEPENDENCIAS[i % len(DEPENDENCIAS)],
                telefono=f"+56 2 2{i:03d}0000",
                mail=f"contacto{rbd}@demo.cl",
                url=f"https://demo.cl/colegio-{i + 1}",
                habilitado_postular=True,
                publicado=True,
                nivel_minimo=nivel_min,
                nivel_maximo=nivel_max,
                director=f"Director/a Demo {i + 1}",
                etiquetas=tags,
                resumen_proyecto=(
                    f"Proyecto educativo demo del colegio {i + 1}, orientado a la "
                    "formación integral y al desarrollo de habilidades para el siglo XXI."
                ),
                internado="INTERNADO" in tags,
                integracion="PIE" in tags,
                subvencion_preferencial="SEP" in tags,
                peib=False,
                alumnos_matriculados=rng.randint(120, 1200),
                promedio_alumnos_por_curso=round(rng.uniform(20, 40), 1),
                cantidad_docentes=rng.randint(10, 80),
                regimen=REGIMENES[i % len(REGIMENES)],
            )
        )
    return ests


def _build_sedes(ests: list[orm.Establecimiento]) -> list[orm.Sede]:
    return [
        orm.Sede(
            rbd=e.rbd,
            codigo_sede=1,
            codigo_region=990,
            codigo_comuna=99001 + (e.rbd % 3),
            region="REGIÓN DEMO",
            comuna=f"COMUNA DEMO {(e.rbd % 3) + 1}",
            calle=f"Calle Demo {e.rbd - RBD_BASE + 1}",
            latitud=round(-33.4 + (e.rbd % 50) * 0.001, 6),
            longitud=round(-70.6 + (e.rbd % 50) * 0.001, 6),
        )
        for e in ests
    ]


def _build_cursos(ests: list[orm.Establecimiento], rng: random.Random) -> list[orm.Curso]:
    cursos = []
    for e in ests:
        for nivel in range(1, rng.randint(3, 7)):
            cursos.append(
                orm.Curso(
                    rbd=e.rbd,
                    codigo_curso=int(f"{e.rbd:06d}{nivel:02d}"),
                    codigo_sede=1,
                    glosa_nivel=f"{nivel}º Nivel",
                    etiqueta_nivel="ENSEÑANZA BÁSICA",
                    sexo="Mixto",
                    glosa_jornada="Jornada Escolar Completa",
                    copago_cuotas=10,
                    copago_valor=rng.randint(0, 150000),
                    cupos_totales=rng.randint(20, 45),
                )
            )
    return cursos


def _build_indicadores(ests: list[orm.Establecimiento], rng: random.Random) -> list[orm.Indicador]:
    inds = []
    for e in ests:
        for tipo in ("SIMCE", "DESARROLLO_PERSONAL"):
            inds.append(
                orm.Indicador(
                    rbd=e.rbd,
                    tipo_indicador=tipo,
                    titulo_indicador=tipo,
                    nombre_indicador=f"Puntaje {tipo.lower().replace('_', ' ')}",
                    puntaje=round(rng.uniform(200, 320), 1),
                    comparacion_gse_numero=rng.randint(0, 2),
                    comparacion_gse_glosa="Similar al grupo socioeconómico",
                )
            )
    return inds


def _build_actividades(ests: list[orm.Establecimiento]) -> list[orm.Actividad]:
    return [
        orm.Actividad(rbd=e.rbd, tipo="Deportes", nombre="Fútbol", nivel="Media", exigencia="Básica")
        for e in ests
    ]


def _build_imagenes(ests: list[orm.Establecimiento]) -> list[orm.Imagen]:
    return [
        orm.Imagen(rbd=e.rbd, nombre="fachada", principal=True)
        for e in ests
    ]


async def seed() -> None:
    rng = random.Random(42)
    ests = _build_establecimientos(rng)
    sedes = _build_sedes(ests)
    cursos = _build_cursos(ests, rng)
    indicadores = _build_indicadores(ests, rng)
    actividades = _build_actividades(ests)
    imagenes = _build_imagenes(ests)

    async with async_session_factory() as session:
        # Idempotencia: borra datos demo previos en orden de FK.
        for model, col in [
            (orm.Imagen, orm.Imagen.rbd),
            (orm.Actividad, orm.Actividad.rbd),
            (orm.Indicador, orm.Indicador.rbd),
            (orm.Curso, orm.Curso.rbd),
            (orm.Sede, orm.Sede.rbd),
        ]:
            await session.execute(delete(model).where(col >= RBD_BASE))
        await session.execute(delete(orm.Establecimiento).where(orm.Establecimiento.rbd >= RBD_BASE))
        await session.execute(delete(orm.Comuna).where(orm.Comuna.codigo >= 99000))
        await session.execute(delete(orm.Region).where(orm.Region.codigo >= 990))

        session.add(orm.Region(codigo=990, nombre="REGIÓN DEMO"))
        await session.flush()

        for i in range(3):
            session.add(orm.Comuna(codigo=99001 + i, nombre=f"COMUNA DEMO {i + 1}", codigo_region=990))
        await session.flush()

        session.add_all(ests)
        await session.flush()

        session.add_all(sedes)
        await session.flush()

        session.add_all(cursos)
        await session.flush()

        session.add_all(indicadores)
        session.add_all(actividades)
        session.add_all(imagenes)

        await session.commit()

    print(f"Seed demo completado: {TOTAL} colegios")
    print(f"  establecimientos: {len(ests)}")
    print(f"  sedes: {len(sedes)}")
    print(f"  cursos: {len(cursos)}")
    print(f"  indicadores: {len(indicadores)}")
    print(f"  actividades: {len(actividades)}")
    print(f"  imagenes: {len(imagenes)}")


if __name__ == "__main__":
    asyncio.run(seed())
