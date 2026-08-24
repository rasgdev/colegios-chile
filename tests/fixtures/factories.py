"""Factories para crear entidades de prueba de forma determinística."""
from __future__ import annotations

from src.infrastructure.db import orm


def region(codigo: int, nombre: str) -> orm.Region:
    return orm.Region(codigo=codigo, nombre=nombre)


def comuna(codigo: int, nombre: str, codigo_region: int) -> orm.Comuna:
    return orm.Comuna(codigo=codigo, nombre=nombre, codigo_region=codigo_region)


def establecimiento(
    rbd: int,
    nombre: str,
    *,
    dependencia: str = "PUBLICO",
    nivel_minimo: str = "Pre-Kinder",
    nivel_maximo: str = "IV Medio",
    regimen: str = "Mixto",
    etiquetas: list[str] | None = None,
    publicado: bool = True,
    **kwargs,
) -> orm.Establecimiento:
    defaults = {
        "telefono": None,
        "mail": None,
        "url": None,
        "habilitado_postular": True,
        "director": None,
        "resumen_proyecto": None,
        "documento_proyecto": None,
        "documento_reglamento": None,
        "internado": False,
        "integracion": False,
        "subvencion_preferencial": False,
        "peib": False,
        "politica_uniforme": None,
        "orientacion_religiosa": None,
        "alumnos_matriculados": None,
        "promedio_alumnos_por_curso": None,
        "cantidad_docentes": None,
    }
    defaults.update(kwargs)
    return orm.Establecimiento(
        rbd=rbd,
        nombre=nombre,
        dependencia=dependencia,
        nivel_minimo=nivel_minimo,
        nivel_maximo=nivel_maximo,
        regimen=regimen,
        etiquetas=etiquetas or [],
        publicado=publicado,
        **defaults,
    )


def sede(
    rbd: int,
    *,
    codigo_sede: int = 1,
    codigo_region: int,
    codigo_comuna: int,
    region: str,
    comuna: str,
    calle: str | None = None,
    latitud: float | None = None,
    longitud: float | None = None,
) -> orm.Sede:
    return orm.Sede(
        rbd=rbd,
        codigo_sede=codigo_sede,
        codigo_region=codigo_region,
        codigo_comuna=codigo_comuna,
        region=region,
        comuna=comuna,
        calle=calle,
        latitud=latitud,
        longitud=longitud,
    )


def curso(
    rbd: int,
    codigo_curso: int,
    *,
    codigo_sede: int = 1,
    copago_valor: int | None = None,
    **kwargs,
) -> orm.Curso:
    defaults = {
        "glosa_grupo_ensenanza": None,
        "glosa_ensenanza": None,
        "glosa_nivel": None,
        "etiqueta_nivel": None,
        "sexo": None,
        "glosa_jornada": None,
        "glosa_especialidad": None,
        "glosa_grupo_pago": None,
        "codigo_ensenanza": None,
        "codigo_nivel": None,
        "codigo_jornada": None,
        "codigo_sexo": None,
        "codigo_especialidad": None,
        "unico_comuna": None,
        "proporcion_excelencia_transicion": None,
        "proporcion_excelencia_regimen": None,
        "proporcion_especializacion_temprana": None,
        "copago_cuotas": None,
        "cupos_totales": None,
        "vacantes_rango_inferior": None,
        "vacantes_rango_superior": None,
        "porcentaje_cambio_inferior": None,
        "porcentaje_cambio_superior": None,
        "repitentes_anio_actual": None,
        "repitentes_nivel_anterior": None,
        "pre_inscritos_anio_siguiente": None,
        "cambios_inferior": None,
        "cambios_superior": None,
        "pre_vacantes_inferior": None,
        "pre_vacantes_superior": None,
        "rango": None,
        "postulantes_anio_anterior": None,
        "movimiento_lista_espera_anterior": None,
    }
    defaults.update(kwargs)
    return orm.Curso(
        rbd=rbd,
        codigo_curso=codigo_curso,
        codigo_sede=codigo_sede,
        copago_valor=copago_valor,
        **defaults,
    )


def indicador(rbd: int, tipo: str, nombre: str, **kwargs) -> orm.Indicador:
    return orm.Indicador(rbd=rbd, tipo_indicador=tipo, nombre_indicador=nombre, **kwargs)


def actividad(rbd: int, nombre: str, tipo: str = "Deportes", **kwargs) -> orm.Actividad:
    return orm.Actividad(rbd=rbd, tipo=tipo, nombre=nombre, **kwargs)


def imagen(rbd: int, nombre: str = "fachada", principal: bool = True, **kwargs) -> orm.Imagen:
    return orm.Imagen(rbd=rbd, nombre=nombre, principal=principal, **kwargs)
