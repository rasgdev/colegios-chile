"""Dataset mínimo determinístico para tests de integración.

Los datos representan una pequeña muestra realista de establecimientos chilenos
con el objetivo de cubrir los casos de test actuales sin depender de ejecutar
el ETL ni de archivos Parquet en CI.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tests.fixtures import factories


async def seed_test_dataset(session: AsyncSession) -> None:
    """Inserta datos de prueba en la sesión dada.

    Limpia las tablas primero para que la función sea idempotente y pueda
    ejecutarse múltiples veces sin errores de duplicados.
    """
    await _truncate_tables(session)

    regiones = _build_regiones()
    comunas = _build_comunas()
    establecimientos = _build_establecimientos()
    sedes = _build_sedes()
    cursos = _build_cursos()
    indicadores = _build_indicadores()
    actividades = _build_actividades()
    imagenes = _build_imagenes()

    for entidades in (regiones, comunas, establecimientos, sedes, cursos, indicadores, actividades, imagenes):
        session.add_all(entidades)
        await session.flush()

    await session.commit()


async def _truncate_tables(session: AsyncSession) -> None:
    """Borra datos de todas las tablas del schema en orden de dependencias FK."""
    from sqlalchemy import text

    tables = [
        "imagenes",
        "actividades",
        "indicadores",
        "cursos",
        "sedes",
        "establecimientos",
        "comunas",
        "regiones",
    ]
    for table in tables:
        await session.execute(text(f"DELETE FROM {table}"))
    await session.flush()


def _build_regiones() -> list:
    return [
        factories.region(1, "Tarapacá"),
        factories.region(2, "Antofagasta"),
        factories.region(3, "Atacama"),
        factories.region(4, "Coquimbo"),
        factories.region(5, "Valparaíso"),
        factories.region(6, "Libertador General Bernardo O'Higgins"),
        factories.region(7, "Maule"),
        factories.region(8, "Biobío"),
        factories.region(9, "La Araucanía"),
        factories.region(10, "Los Lagos"),
        factories.region(11, "Aysén del General Carlos Ibáñez del Campo"),
        factories.region(12, "Magallanes y de la Antártica Chilena"),
        factories.region(13, "Metropolitana de Santiago"),
        factories.region(14, "Los Ríos"),
        factories.region(15, "Arica y Parinacota"),
        factories.region(16, "Ñuble"),
    ]


def _build_comunas() -> list:
    return [
        factories.comuna(13101, "Santiago", 13),
        factories.comuna(13102, "Puente Alto", 13),
        factories.comuna(13103, "Maipú", 13),
        factories.comuna(13104, "Las Condes", 13),
        factories.comuna(13105, "La Florida", 13),
        factories.comuna(13106, "San Bernardo", 13),
        factories.comuna(13107, "Ñuñoa", 13),
        factories.comuna(13108, "La Pintana", 13),
        factories.comuna(5101, "Valparaíso", 5),
        factories.comuna(8101, "Concepción", 8),
    ]


def _build_establecimientos() -> list:
    return [
        factories.establecimiento(
            60,
            "Colegio Aleman de Santiago",
            dependencia="PUBLICO",
            nivel_minimo="Pre-Kinder",
            nivel_maximo="IV Medio",
            regimen="Mixto",
            etiquetas=["GRATUITO", "PIE"],
            alumnos_matriculados=1200,
            cantidad_docentes=80,
        ),
        factories.establecimiento(
            22248,
            "Liceo Municipal de Puente Alto",
            dependencia="PUBLICO",
            nivel_minimo="1º Básico",
            nivel_maximo="IV Medio",
            regimen="Mixto",
            etiquetas=["GRATUITO"],
            alumnos_matriculados=900,
            cantidad_docentes=55,
        ),
        factories.establecimiento(
            1001,
            "Colegio Particular Los Andes",
            dependencia="PARTICULAR SUBVENCIONADO",
            nivel_minimo="Pre-Kinder",
            nivel_maximo="8º Básico",
            regimen="Mixto",
            etiquetas=["SEP"],
            alumnos_matriculados=600,
            cantidad_docentes=35,
        ),
        factories.establecimiento(
            1002,
            "Instituto Técnico Profesional Maipú",
            dependencia="PUBLICO",
            nivel_minimo="7º Básico",
            nivel_maximo="IV Medio",
            regimen="Hombres",
            etiquetas=["TECNICO_PROFESIONAL", "GRATUITO"],
            alumnos_matriculados=750,
            cantidad_docentes=40,
        ),
        factories.establecimiento(
            1003,
            "Escuela Básica Las Condes",
            dependencia="PUBLICO",
            nivel_minimo="1º Básico",
            nivel_maximo="8º Básico",
            regimen="Mixto",
            etiquetas=["GRATUITO"],
            alumnos_matriculados=450,
            cantidad_docentes=25,
        ),
        factories.establecimiento(
            1004,
            "Liceo de Niñas La Florida",
            dependencia="SERVICIO LOCAL DE EDUCACIÓN",
            nivel_minimo="7º Básico",
            nivel_maximo="IV Medio",
            regimen="Mujeres",
            etiquetas=["GRATUITO", "INTERNADO"],
            alumnos_matriculados=520,
            cantidad_docentes=30,
        ),
    ]


def _build_sedes() -> list:
    return [
        factories.sede(60, codigo_region=13, codigo_comuna=13101, region="Metropolitana de Santiago", comuna="Santiago"),
        factories.sede(22248, codigo_region=13, codigo_comuna=13102, region="Metropolitana de Santiago", comuna="Puente Alto"),
        factories.sede(1001, codigo_region=13, codigo_comuna=13103, region="Metropolitana de Santiago", comuna="Maipú"),
        factories.sede(1002, codigo_region=13, codigo_comuna=13104, region="Metropolitana de Santiago", comuna="Las Condes"),
        factories.sede(1003, codigo_region=13, codigo_comuna=13105, region="Metropolitana de Santiago", comuna="La Florida"),
        factories.sede(1004, codigo_region=13, codigo_comuna=13106, region="Metropolitana de Santiago", comuna="San Bernardo"),
    ]


def _build_cursos() -> list:
    cursos = []
    for rbd in (60, 22248, 1001, 1002, 1003, 1004):
        cursos.append(factories.curso(rbd, rbd * 1000 + 1, copago_valor=15000))
        cursos.append(factories.curso(rbd, rbd * 1000 + 2, copago_valor=25000))
        cursos.append(factories.curso(rbd, rbd * 1000 + 3, copago_valor=35000))
    return cursos


def _build_indicadores() -> list:
    return [
        factories.indicador(60, "SIMCE", "Puntaje SIMCE", puntaje=280.0),
        factories.indicador(60, "DESARROLLO_PERSONAL", "Puntaje desarrollo personal", puntaje=300.0),
        factories.indicador(22248, "SIMCE", "Puntaje SIMCE", puntaje=260.0),
        factories.indicador(1001, "SIMCE", "Puntaje SIMCE", puntaje=270.0),
        factories.indicador(1002, "SIMCE", "Puntaje SIMCE", puntaje=265.0),
        factories.indicador(1003, "SIMCE", "Puntaje SIMCE", puntaje=275.0),
        factories.indicador(1004, "SIMCE", "Puntaje SIMCE", puntaje=255.0),
    ]


def _build_actividades() -> list:
    return [
        factories.actividad(60, "Fútbol"),
        factories.actividad(60, "Teatro"),
        factories.actividad(22248, "Básquetbol"),
        factories.actividad(1001, "Robótica"),
        factories.actividad(1002, "Ajedrez"),
        factories.actividad(1003, "Coro"),
        factories.actividad(1004, "Danza"),
    ]


def _build_imagenes() -> list:
    return [
        factories.imagen(60, "fachada", principal=True),
        factories.imagen(22248, "fachada", principal=True),
        factories.imagen(1001, "fachada", principal=True),
        factories.imagen(1002, "fachada", principal=True),
        factories.imagen(1003, "fachada", principal=True),
        factories.imagen(1004, "fachada", principal=True),
    ]
