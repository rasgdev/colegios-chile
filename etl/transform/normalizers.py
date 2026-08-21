import json
from pathlib import Path
from typing import Any

import polars as pl
import structlog
from pydantic import ValidationError

from config.settings import settings
from etl.transform.models import EstablecimientoDetalle

logger = structlog.get_logger()


def _cargar_detalle(path: Path) -> EstablecimientoDetalle:
    data = json.loads(path.read_text())
    return EstablecimientoDetalle.model_validate(data)


def _cargar_todos_los_detalles() -> list[EstablecimientoDetalle]:
    raw_dir = settings.establecimientos_raw_dir
    archivos = sorted(raw_dir.glob("*.json"))
    detalles: list[EstablecimientoDetalle] = []

    for path in archivos:
        try:
            detalle = _cargar_detalle(path)
            detalles.append(detalle)
        except (json.JSONDecodeError, ValidationError):
            logger.exception("json_invalido", archivo=str(path))

    logger.info("detalles_cargados", total=len(detalles), archivos=len(archivos))
    return detalles


def _extraer_director_nombre(d: EstablecimientoDetalle) -> str | None:
    if d.director:
        return d.director.nombre
    return None


def _extraer_info(key: str, d: EstablecimientoDetalle, default: Any = None) -> Any:
    if d.informacionInstitucional:
        return getattr(d.informacionInstitucional, key, default)
    return default


def construir_establecimientos(detalles: list[EstablecimientoDetalle]) -> pl.DataFrame:
    rows = []
    for d in detalles:
        rows.append({
            "rbd": d.rbd,
            "nombre": d.nombre,
            "dependencia": d.dependencia,
            "telefono": d.telefono,
            "mail": d.mail,
            "url": d.url,
            "habilitado_postular": d.habilitadoPostular,
            "habilitado_vitrina": d.habilitadoVitrina,
            "nivel_minimo": d.nivelMinimo,
            "nivel_maximo": d.nivelMaximo,
            "director": _extraer_director_nombre(d),
            "etiquetas": ",".join(d.etiquetas) if d.etiquetas else None,
            "resumen_proyecto": _extraer_info("resumenProyecto", d),
            "documento_proyecto": _extraer_info("documentoProyecto", d),
            "documento_reglamento": _extraer_info("documentoReglamento", d),
            "internado": _extraer_info("internado", d),
            "integracion": _extraer_info("integracion", d),
            "subvencion_preferencial": _extraer_info("subvencionPreferencial", d),
            "peib": _extraer_info("peib", d),
            "politica_uniforme": _extraer_info("politicaUniforme", d),
            "orientacion_religiosa": _extraer_info("orientacionReligiosa", d),
            "alumnos_matriculados": _extraer_info("alumnosMatriculados", d),
            "promedio_alumnos_por_curso": _extraer_info("promedioAlumnosPorCurso", d),
            "cantidad_docentes": _extraer_info("cantidadDocentes", d),
            "regimen": _extraer_info("regimen", d),
            "distancia": d.distancia,
            "id_mongo": d.id,
        })

    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows)


def construir_sedes(detalles: list[EstablecimientoDetalle]) -> pl.DataFrame:
    rows = []
    for d in detalles:
        for sede in d.sedes:
            direccion = sede.direccion
            row: dict[str, Any] = {
                "rbd": d.rbd,
                "codigo_sede": sede.codigoSede,
            }
            if direccion:
                coord = direccion.coordenadas
                row.update({
                    "codigo_region": direccion.codigoRegion,
                    "codigo_comuna": direccion.codigoComuna,
                    "region": direccion.region,
                    "comuna": direccion.comuna,
                    "calle": direccion.calle,
                    "longitud": coord.coordinates[0] if coord and len(coord.coordinates) >= 1 else None,
                    "latitud": coord.coordinates[1] if coord and len(coord.coordinates) >= 2 else None,
                })
            rows.append(row)

    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows)


def construir_cursos(detalles: list[EstablecimientoDetalle]) -> pl.DataFrame:
    rows = []
    for d in detalles:
        for sede in d.sedes:
            for nivel in sede.niveles:
                copago = nivel.copago
                rows.append({
                    "rbd": d.rbd,
                    "codigo_sede": sede.codigoSede,
                    "codigo_curso": nivel.codigoCurso,
                    "glosa_grupo_ensenanza": nivel.glosaGrupoEnsenanza,
                    "glosa_ensenanza": nivel.glosaEnsenanza,
                    "glosa_nivel": nivel.glosaNivel,
                    "etiqueta_nivel": nivel.etiquetaNivel,
                    "sexo": nivel.sexo,
                    "glosa_jornada": nivel.glosaJornada,
                    "glosa_especialidad": nivel.glosaEspecialidad,
                    "glosa_grupo_pago": nivel.glosaGrupoPago,
                    "codigo_ensenanza": nivel.codigoEnsenanza,
                    "codigo_nivel": nivel.codigoNivel,
                    "codigo_jornada": nivel.codigoJornada,
                    "codigo_sexo": nivel.codigoSexo,
                    "codigo_especialidad": nivel.codigoEspecialidad,
                    "unico_comuna": nivel.unicoComuna,
                    "proporcion_excelencia_transicion": nivel.proporcionExcelenciaTransicion,
                    "proporcion_excelencia_regimen": nivel.proporcionExcelenciaRegimen,
                    "proporcion_especializacion_temprana": nivel.proporcionEspecializacionTemprana,
                    "copago_cuotas": copago.numeroCuotas if copago else None,
                    "copago_valor": copago.valorCuota if copago else None,
                    "cupos_totales": nivel.cuposTotales,
                    "vacantes_rango_inferior": nivel.numeroVacantesRangoInferior,
                    "vacantes_rango_superior": nivel.numeroVacantesRangoSuperior,
                    "porcentaje_cambio_inferior": nivel.porcentajeCambioInferior,
                    "porcentaje_cambio_superior": nivel.procentajeCambioSuperior,
                    "repitentes_anio_actual": nivel.cantidadRepitentesAnioActual,
                    "repitentes_nivel_anterior": nivel.cantidadRepitentesNivelAnterior,
                    "pre_inscritos_anio_siguiente": nivel.cantidadPreInscritosAnioSiguiente,
                    "cambios_inferior": nivel.cambiosInferior,
                    "cambios_superior": nivel.cambiosSuperior,
                    "pre_vacantes_inferior": nivel.cantidadPreVacantesInferior,
                    "pre_vacantes_superior": nivel.cantidadPreVacantesSuperior,
                    "rango": nivel.rango,
                    "postulantes_anio_anterior": nivel.numeroPostulantesAnioAnterior,
                    "movimiento_lista_espera_anterior": nivel.numeroMovimientoListaEsperaAnoAnterior,
                })

    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows)


def construir_actividades(detalles: list[EstablecimientoDetalle]) -> pl.DataFrame:
    rows = []
    for d in detalles:
        for act in d.actividades:
            rows.append({
                "rbd": d.rbd,
                "tipo": act.tipo,
                "nombre": act.nombre,
                "nivel": act.nivel,
                "exigencia": act.exigencia,
            })

    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows)


def construir_indicadores(detalles: list[EstablecimientoDetalle]) -> pl.DataFrame:
    rows = []
    for d in detalles:
        for ind in d.indicadores:
            for clas in ind.clasificaciones:
                rows.append({
                    "rbd": d.rbd,
                    "tipo_indicador": ind.tipo,
                    "titulo_indicador": ind.titulo,
                    "nivel_indicador": ind.nivel,
                    "descripcion_indicador": ind.descripcion,
                    "nombre_indicador": clas.nombreIndicador,
                    "puntaje": clas.puntaje,
                    "comparacion_gse_numero": clas.comparacionGseNumero,
                    "comparacion_gse_glosa": clas.comparacionGseGlosa,
                })

    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows)


def construir_imagenes(detalles: list[EstablecimientoDetalle]) -> pl.DataFrame:
    rows = []
    for d in detalles:
        for img in d.imagenes:
            rows.append({
                "rbd": d.rbd,
                "nombre": img.nombre,
                "principal": img.principal,
            })

    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows)


def transformar_todo() -> dict[str, pl.DataFrame]:
    detalles = _cargar_todos_los_detalles()

    return {
        "establecimientos": construir_establecimientos(detalles),
        "sedes": construir_sedes(detalles),
        "cursos": construir_cursos(detalles),
        "actividades": construir_actividades(detalles),
        "indicadores": construir_indicadores(detalles),
        "imagenes": construir_imagenes(detalles),
    }
