"""Modelos ORM (SQLAlchemy 2.0 declarative).

Espejo del DDL de Alembic (migración 0001). Solo lectura: la app consulta;
el loader (`src/infrastructure/loader.py`) es quien escribe.
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    Identity,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Region(Base):
    __tablename__ = "regiones"

    codigo: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, unique=True)


class Comuna(Base):
    __tablename__ = "comunas"

    codigo: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text)
    codigo_region: Mapped[int] = mapped_column(Integer)


class Establecimiento(Base):
    __tablename__ = "establecimientos"

    rbd: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text)
    dependencia: Mapped[str] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(Text)
    mail: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    habilitado_postular: Mapped[bool] = mapped_column(Boolean, default=True)
    publicado: Mapped[bool] = mapped_column(Boolean, default=False)
    nivel_minimo: Mapped[str | None] = mapped_column(Text)
    nivel_maximo: Mapped[str | None] = mapped_column(Text)
    director: Mapped[str | None] = mapped_column(Text)
    etiquetas: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    resumen_proyecto: Mapped[str | None] = mapped_column(Text)
    documento_proyecto: Mapped[str | None] = mapped_column(Text)
    documento_reglamento: Mapped[str | None] = mapped_column(Text)
    internado: Mapped[bool] = mapped_column(Boolean, default=False)
    integracion: Mapped[bool] = mapped_column(Boolean, default=False)
    subvencion_preferencial: Mapped[bool] = mapped_column(Boolean, default=False)
    peib: Mapped[bool] = mapped_column(Boolean, default=False)
    politica_uniforme: Mapped[str | None] = mapped_column(Text)
    orientacion_religiosa: Mapped[str | None] = mapped_column(Text)
    alumnos_matriculados: Mapped[int | None] = mapped_column(Integer)
    promedio_alumnos_por_curso: Mapped[float | None] = mapped_column(Float)
    cantidad_docentes: Mapped[int | None] = mapped_column(Integer)
    regimen: Mapped[str | None] = mapped_column(Text)


class Sede(Base):
    __tablename__ = "sedes"

    rbd: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_sede: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_region: Mapped[int] = mapped_column(Integer)
    codigo_comuna: Mapped[int] = mapped_column(Integer)
    region: Mapped[str] = mapped_column(Text)
    comuna: Mapped[str] = mapped_column(Text)
    calle: Mapped[str | None] = mapped_column(Text)
    latitud: Mapped[float | None] = mapped_column(Float)
    longitud: Mapped[float | None] = mapped_column(Float)


class Curso(Base):
    __tablename__ = "cursos"

    rbd: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_curso: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    codigo_sede: Mapped[int] = mapped_column(Integer)
    glosa_grupo_ensenanza: Mapped[str | None] = mapped_column(Text)
    glosa_ensenanza: Mapped[str | None] = mapped_column(Text)
    glosa_nivel: Mapped[str | None] = mapped_column(Text)
    etiqueta_nivel: Mapped[str | None] = mapped_column(Text)
    sexo: Mapped[str | None] = mapped_column(Text)
    glosa_jornada: Mapped[str | None] = mapped_column(Text)
    glosa_especialidad: Mapped[str | None] = mapped_column(Text)
    glosa_grupo_pago: Mapped[str | None] = mapped_column(Text)
    codigo_ensenanza: Mapped[int | None] = mapped_column(Integer)
    codigo_nivel: Mapped[int | None] = mapped_column(Integer)
    codigo_jornada: Mapped[int | None] = mapped_column(Integer)
    codigo_sexo: Mapped[int | None] = mapped_column(Integer)
    codigo_especialidad: Mapped[int | None] = mapped_column(Integer)
    unico_comuna: Mapped[bool | None] = mapped_column(Boolean)
    proporcion_excelencia_transicion: Mapped[float | None] = mapped_column(Float)
    proporcion_excelencia_regimen: Mapped[float | None] = mapped_column(Float)
    proporcion_especializacion_temprana: Mapped[float | None] = mapped_column(Float)
    copago_cuotas: Mapped[int | None] = mapped_column(Integer)
    copago_valor: Mapped[int | None] = mapped_column(Integer)
    cupos_totales: Mapped[int | None] = mapped_column(Integer)
    vacantes_rango_inferior: Mapped[int | None] = mapped_column(Integer)
    vacantes_rango_superior: Mapped[int | None] = mapped_column(Integer)
    porcentaje_cambio_inferior: Mapped[float | None] = mapped_column(Float)
    porcentaje_cambio_superior: Mapped[float | None] = mapped_column(Float)
    repitentes_anio_actual: Mapped[int | None] = mapped_column(Integer)
    repitentes_nivel_anterior: Mapped[int | None] = mapped_column(Integer)
    pre_inscritos_anio_siguiente: Mapped[int | None] = mapped_column(Integer)
    cambios_inferior: Mapped[int | None] = mapped_column(Integer)
    cambios_superior: Mapped[int | None] = mapped_column(Integer)
    pre_vacantes_inferior: Mapped[int | None] = mapped_column(Integer)
    pre_vacantes_superior: Mapped[int | None] = mapped_column(Integer)
    rango: Mapped[int | None] = mapped_column(Integer)
    postulantes_anio_anterior: Mapped[int | None] = mapped_column(Integer)
    movimiento_lista_espera_anterior: Mapped[int | None] = mapped_column(Integer)


class Indicador(Base):
    __tablename__ = "indicadores"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    rbd: Mapped[int] = mapped_column(Integer)
    tipo_indicador: Mapped[str] = mapped_column(Text)
    titulo_indicador: Mapped[str | None] = mapped_column(Text)
    nivel_indicador: Mapped[str | None] = mapped_column(Text)
    descripcion_indicador: Mapped[str | None] = mapped_column(Text)
    nombre_indicador: Mapped[str] = mapped_column(Text)
    puntaje: Mapped[float | None] = mapped_column(Float)
    comparacion_gse_numero: Mapped[int | None] = mapped_column(Integer)
    comparacion_gse_glosa: Mapped[str | None] = mapped_column(Text)


class Actividad(Base):
    __tablename__ = "actividades"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    rbd: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str | None] = mapped_column(Text)
    nombre: Mapped[str] = mapped_column(Text)
    nivel: Mapped[str | None] = mapped_column(Text)
    exigencia: Mapped[str | None] = mapped_column(Text)


class Imagen(Base):
    __tablename__ = "imagenes"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    rbd: Mapped[int] = mapped_column(Integer)
    nombre: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    principal: Mapped[bool] = mapped_column(Boolean, default=False)
