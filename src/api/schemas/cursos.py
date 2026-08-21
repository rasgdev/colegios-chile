"""DTOs de cursos (completo y resumen)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CursoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rbd: int
    codigo_curso: int
    codigo_sede: int
    glosa_grupo_ensenanza: str | None = None
    glosa_ensenanza: str | None = None
    glosa_nivel: str | None = None
    etiqueta_nivel: str | None = None
    sexo: str | None = None
    glosa_jornada: str | None = None
    glosa_especialidad: str | None = None
    glosa_grupo_pago: str | None = None
    codigo_ensenanza: int | None = None
    codigo_nivel: int | None = None
    codigo_jornada: int | None = None
    codigo_sexo: int | None = None
    codigo_especialidad: int | None = None
    unico_comuna: bool | None = None
    proporcion_excelencia_transicion: float | None = None
    proporcion_excelencia_regimen: float | None = None
    proporcion_especializacion_temprana: float | None = None
    copago_cuotas: int | None = None
    copago_valor: int | None = None
    cupos_totales: int | None = None
    vacantes_rango_inferior: int | None = None
    vacantes_rango_superior: int | None = None
    porcentaje_cambio_inferior: float | None = None
    porcentaje_cambio_superior: float | None = None
    repitentes_anio_actual: int | None = None
    repitentes_nivel_anterior: int | None = None
    pre_inscritos_anio_siguiente: int | None = None
    cambios_inferior: int | None = None
    cambios_superior: int | None = None
    pre_vacantes_inferior: int | None = None
    pre_vacantes_superior: int | None = None
    rango: int | None = None
    postulantes_anio_anterior: int | None = None
    movimiento_lista_espera_anterior: int | None = None


class CursoResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo_curso: int
    glosa_nivel: str | None = None
    etiqueta_nivel: str | None = None
    sexo: str | None = None
    glosa_jornada: str | None = None
    copago_cuotas: int | None = None
    copago_valor: int | None = None
    cupos_totales: int | None = None
