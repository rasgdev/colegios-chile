from typing import Any, Optional

from pydantic import BaseModel, Field


class Coordenadas(BaseModel):
    type: str = "Point"
    coordinates: list[float]


class Direccion(BaseModel):
    codigoRegion: int
    codigoComuna: int
    region: str
    comuna: str
    calle: str
    coordenadas: Optional[Coordenadas] = None


class Copago(BaseModel):
    numeroCuotas: Optional[int] = None
    valorCuota: Optional[int] = None


class Nivel(BaseModel):
    codigoCurso: int
    glosaGrupoEnsenanza: Optional[str] = None
    glosaEnsenanza: Optional[str] = None
    glosaNivel: Optional[str] = None
    etiquetaNivel: Optional[str] = None
    sexo: Optional[str] = None
    glosaJornada: Optional[str] = None
    glosaEspecialidad: Optional[str] = None
    glosaGrupoPago: Optional[str] = None
    codigoEnsenanza: Optional[int] = None
    codigoNivel: Optional[int] = None
    codigoJornada: Optional[int] = None
    codigoSexo: Optional[int] = None
    codigoEspecialidad: Optional[int] = None
    unicoComuna: Optional[bool] = None
    proporcionExcelenciaTransicion: Optional[float] = None
    proporcionExcelenciaRegimen: Optional[float] = None
    proporcionEspecializacionTemprana: Optional[float] = None
    copago: Optional[Copago] = None
    cuposTotales: Optional[int] = None
    numeroVacantesRangoInferior: Optional[int] = None
    numeroVacantesRangoSuperior: Optional[int] = None
    porcentajeCambioInferior: Optional[float] = None
    procentajeCambioSuperior: Optional[float] = None
    cantidadRepitentesAnioActual: Optional[int] = None
    cantidadRepitentesNivelAnterior: Optional[int] = None
    cantidadPreInscritosAnioSiguiente: Optional[int] = None
    cambiosInferior: Optional[int] = None
    cambiosSuperior: Optional[int] = None
    cantidadPreVacantesInferior: Optional[int] = None
    cantidadPreVacantesSuperior: Optional[int] = None
    rango: Optional[int] = None
    numeroPostulantesAnioAnterior: Optional[int] = None
    numeroMovimientoListaEsperaAnoAnterior: Optional[int] = None


class Sede(BaseModel):
    codigoSede: int
    direccion: Optional[Direccion] = None
    niveles: list[Nivel] = Field(default_factory=list)


class Director(BaseModel):
    nombre: str


class InformacionInstitucional(BaseModel):
    resumenProyecto: Optional[str] = None
    documentoProyecto: Optional[str] = None
    documentoReglamento: Optional[str] = None
    internado: Optional[bool] = None
    integracion: Optional[bool] = None
    resumenProyectoPIE: Optional[str] = None
    subvencionPreferencial: Optional[bool] = None
    peib: Optional[bool] = None
    politicaUniforme: Optional[str] = None
    orientacionReligiosa: Optional[str] = None
    alumnosMatriculados: Optional[int] = None
    promedioAlumnosPorCurso: Optional[float] = None
    cantidadDocentes: Optional[int] = None
    regimen: Optional[str] = None


class Imagen(BaseModel):
    nombre: Optional[str] = None
    principal: Optional[bool] = None


class Actividad(BaseModel):
    tipo: Optional[str] = None
    nombre: Optional[str] = None
    nivel: Optional[str] = None
    exigencia: Optional[str] = None


class ClasificacionIndicador(BaseModel):
    nombreIndicador: Optional[str] = None
    puntaje: Optional[int] = None
    comparacionGseNumero: Optional[int] = None
    comparacionGseGlosa: Optional[str] = None


class Indicador(BaseModel):
    tipo: Optional[str] = None
    titulo: Optional[str] = None
    nivel: Optional[str] = None
    descripcion: Optional[str] = None
    clasificaciones: list[ClasificacionIndicador] = Field(default_factory=list)


class EstablecimientoDetalle(BaseModel):
    id: Optional[str] = None
    rbd: int
    nombre: Optional[str] = None
    dependencia: Optional[str] = None
    telefono: Optional[str] = None
    mail: Optional[str] = None
    url: Optional[str] = None
    habilitadoPostular: Optional[bool] = None
    habilitadoVitrina: Optional[bool] = None
    nivelMinimo: Optional[str] = None
    nivelMaximo: Optional[str] = None
    director: Optional[Director] = None
    etiquetas: list[str] = Field(default_factory=list)
    informacionInstitucional: Optional[InformacionInstitucional] = None
    sedes: list[Sede] = Field(default_factory=list)
    imagenes: list[Imagen] = Field(default_factory=list)
    distancia: Optional[float] = None
    actividades: list[Actividad] = Field(default_factory=list)
    procesosEspeciales: list[Any] = Field(default_factory=list)
    indicadores: list[Indicador] = Field(default_factory=list)
    especialidades: list[Any] = Field(default_factory=list)


class EstablecimientoBasico(BaseModel):
    rbd: int
    nombre: Optional[str] = None
    dependencia: Optional[str] = None
    habilitadoPostular: Optional[bool] = None
    nivelMinimo: Optional[str] = None
    nivelMaximo: Optional[str] = None
    etiquetas: list[str] = Field(default_factory=list)
    informacionInstitucional: Optional[InformacionInstitucional] = None
    sedes: list[Sede] = Field(default_factory=list)
    imagenes: list[Imagen] = Field(default_factory=list)
    distancia: Optional[float] = None
    procesosEspeciales: list[Any] = Field(default_factory=list)
