"""Entidades de dominio.

Dataclasses planas (stdlib, sin frameworks) que modelan el catálogo del buscador.
El dominio es read-only: los datos provienen del ETL y solo se consultan.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── Niveles educativos: grados concretos → categorías ─────────────────────────
# `nivel_minimo` / `nivel_maximo` en los datos son grados concretos
# ("Pre-Kinder", "1º Básico", ... "IV Medio"), no las categorías PARVULARIO/BASICA/MEDIA.
# Este mapa ordena los grados y los agrupa en categorías para el filtro `nivel=`.

NIVELES_ORDENADOS: list[str] = [
    "Pre-Kinder",
    "Kinder",
    "1º Básico",
    "2º Básico",
    "3º Básico",
    "4º Básico",
    "5º Básico",
    "6º Básico",
    "7º Básico",
    "8º Básico",
    "I Medio",
    "II Medio",
    "III Medio",
    "IV Medio",
]

NIVEL_ORDEN: dict[str, int] = {grado: i for i, grado in enumerate(NIVELES_ORDENADOS)}

CATEGORIAS_NIVEL: dict[str, tuple[str, ...]] = {
    "PARVULARIO": ("Pre-Kinder", "Kinder"),
    "BASICA": ("1º Básico", "2º Básico", "3º Básico", "4º Básico", "5º Básico",
               "6º Básico", "7º Básico", "8º Básico"),
    "MEDIA": ("I Medio", "II Medio", "III Medio", "IV Medio"),
}

# Valores observados en el dataset (documentación / validación de filtros).
DEPENDENCIAS_VALIDAS: tuple[str, ...] = (
    "PUBLICO",
    "PARTICULAR SUBVENCIONADO",
    "SERVICIO LOCAL DE EDUCACIÓN",
)

REGIMENES_VALIDOS: tuple[str, ...] = ("Mixto", "Hombres", "Mujeres")

ETIQUETAS_VALIDAS: tuple[str, ...] = (
    "GRATUITO",
    "INTERNADO",
    "PIE",
    "SEP",
    "TECNICO_PROFESIONAL",
    "_4MEDIO",
)

NIVELES_VALIDOS: tuple[str, ...] = tuple(CATEGORIAS_NIVEL.keys())


def rango_indices_categoria(nivel: str) -> tuple[int, int]:
    """Índices [min, max] de los grados que componen una categoría de nivel."""
    grados = CATEGORIAS_NIVEL[nivel.upper()]
    indices = [NIVEL_ORDEN[g] for g in grados]
    return min(indices), max(indices)


# ── Entidades ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Region:
    codigo: int
    nombre: str


@dataclass(frozen=True)
class Comuna:
    codigo: int
    nombre: str
    codigo_region: int


@dataclass(frozen=True)
class Establecimiento:
    rbd: int
    nombre: str
    dependencia: str
    telefono: str | None = None
    mail: str | None = None
    url: str | None = None
    habilitado_postular: bool = True
    publicado: bool = False
    nivel_minimo: str | None = None
    nivel_maximo: str | None = None
    director: str | None = None
    etiquetas: list[str] = field(default_factory=list)
    resumen_proyecto: str | None = None
    documento_proyecto: str | None = None
    documento_reglamento: str | None = None
    internado: bool = False
    integracion: bool = False
    subvencion_preferencial: bool = False
    peib: bool = False
    politica_uniforme: str | None = None
    orientacion_religiosa: str | None = None
    alumnos_matriculados: int | None = None
    promedio_alumnos_por_curso: float | None = None
    cantidad_docentes: int | None = None
    regimen: str | None = None
    comuna: str | None = None
    region: str | None = None


@dataclass(frozen=True)
class Sede:
    rbd: int
    codigo_sede: int
    codigo_region: int
    codigo_comuna: int
    region: str
    comuna: str
    calle: str | None = None
    latitud: float | None = None
    longitud: float | None = None


@dataclass(frozen=True)
class Curso:
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


@dataclass(frozen=True)
class CursoResumen:
    """Subconjunto esencial de un curso para la ficha (payload liviano)."""

    codigo_curso: int
    glosa_nivel: str | None = None
    etiqueta_nivel: str | None = None
    sexo: str | None = None
    glosa_jornada: str | None = None
    copago_cuotas: int | None = None
    copago_valor: int | None = None
    cupos_totales: int | None = None


@dataclass(frozen=True)
class Indicador:
    id: int
    rbd: int
    tipo_indicador: str
    nombre_indicador: str
    titulo_indicador: str | None = None
    nivel_indicador: str | None = None
    descripcion_indicador: str | None = None
    puntaje: float | None = None
    comparacion_gse_numero: int | None = None
    comparacion_gse_glosa: str | None = None


@dataclass(frozen=True)
class Actividad:
    id: int
    rbd: int
    nombre: str
    tipo: str | None = None
    nivel: str | None = None
    exigencia: str | None = None


@dataclass(frozen=True)
class Imagen:
    id: int
    rbd: int
    nombre: str | None = None
    url: str | None = None
    principal: bool = False


@dataclass(frozen=True)
class Ficha:
    """Agregado enriquecido devuelto por el backend para la ficha de un colegio."""

    establecimiento: Establecimiento
    sedes: list[Sede]
    cursos_resumen: list[CursoResumen]
    indicadores: list[Indicador]
    actividades: list[Actividad]
    imagenes: list[Imagen]


@dataclass(frozen=True)
class SearchQuery:
    """Parámetros de búsqueda (filtros + paginación)."""

    q: str | None = None
    comuna: str | None = None
    region: int | None = None
    dependencia: str | None = None
    regimen: str | None = None
    nivel: str | None = None
    copago_max: int | None = None
    etiquetas: list[str] = field(default_factory=list)
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class SearchPage:
    items: list[Establecimiento]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class CompareResult:
    establecimientos: list[Establecimiento]
    indicadores: dict[int, list[Indicador]]
    cursos_resumen: dict[int, list[CursoResumen]]
    sedes: dict[int, list[Sede]]
