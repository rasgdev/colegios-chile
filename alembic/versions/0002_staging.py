"""tablas de staging para el loader atómico

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-20

Tablas temporales `*_staging` que reciben los datos crudos del Parquet antes del
swap transaccional. Solo columnas insertables (sin `busqueda_tsvector` generado
ni `id` identity) y sin constraints, para poder cargar y validar antes de tocar
las tablas finales.

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE regiones_staging (
            codigo INTEGER,
            nombre TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE comunas_staging (
            codigo INTEGER,
            nombre TEXT,
            codigo_region INTEGER
        )
        """
    )
    op.execute(
        """
        CREATE TABLE establecimientos_staging (
            rbd INTEGER, nombre TEXT, dependencia TEXT, telefono TEXT, mail TEXT, url TEXT,
            habilitado_postular BOOLEAN, publicado BOOLEAN, nivel_minimo TEXT, nivel_maximo TEXT,
            director TEXT, etiquetas TEXT[], resumen_proyecto TEXT,
            documento_proyecto TEXT, documento_reglamento TEXT,
            internado BOOLEAN, integracion BOOLEAN, subvencion_preferencial BOOLEAN, peib BOOLEAN,
            politica_uniforme TEXT, orientacion_religiosa TEXT,
            alumnos_matriculados INTEGER, promedio_alumnos_por_curso FLOAT,
            cantidad_docentes INTEGER, regimen TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE sedes_staging (
            rbd INTEGER, codigo_sede INTEGER, codigo_region INTEGER, codigo_comuna INTEGER,
            region TEXT, comuna TEXT, calle TEXT, latitud FLOAT, longitud FLOAT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE cursos_staging (
            rbd INTEGER, codigo_curso BIGINT, codigo_sede INTEGER,
            glosa_grupo_ensenanza TEXT, glosa_ensenanza TEXT, glosa_nivel TEXT,
            etiqueta_nivel TEXT, sexo TEXT, glosa_jornada TEXT, glosa_especialidad TEXT,
            glosa_grupo_pago TEXT, codigo_ensenanza INTEGER, codigo_nivel INTEGER,
            codigo_jornada INTEGER, codigo_sexo INTEGER, codigo_especialidad INTEGER,
            unico_comuna BOOLEAN,
            proporcion_excelencia_transicion FLOAT, proporcion_excelencia_regimen FLOAT,
            proporcion_especializacion_temprana FLOAT, copago_cuotas INTEGER, copago_valor INTEGER,
            cupos_totales INTEGER, vacantes_rango_inferior INTEGER, vacantes_rango_superior INTEGER,
            porcentaje_cambio_inferior FLOAT, porcentaje_cambio_superior FLOAT,
            repitentes_anio_actual INTEGER, repitentes_nivel_anterior INTEGER,
            pre_inscritos_anio_siguiente INTEGER, cambios_inferior INTEGER, cambios_superior INTEGER,
            pre_vacantes_inferior INTEGER, pre_vacantes_superior INTEGER, rango INTEGER,
            postulantes_anio_anterior INTEGER, movimiento_lista_espera_anterior INTEGER
        )
        """
    )
    op.execute(
        """
        CREATE TABLE indicadores_staging (
            rbd INTEGER, tipo_indicador TEXT, titulo_indicador TEXT, nivel_indicador TEXT,
            descripcion_indicador TEXT, nombre_indicador TEXT, puntaje FLOAT,
            comparacion_gse_numero INTEGER, comparacion_gse_glosa TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE actividades_staging (
            rbd INTEGER, tipo TEXT, nombre TEXT, nivel TEXT, exigencia TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE imagenes_staging (
            rbd INTEGER, nombre TEXT, url TEXT, principal BOOLEAN
        )
        """
    )


def downgrade() -> None:
    for t in [
        "imagenes_staging", "actividades_staging", "indicadores_staging",
        "cursos_staging", "sedes_staging", "establecimientos_staging",
        "comunas_staging", "regiones_staging",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {t}")
