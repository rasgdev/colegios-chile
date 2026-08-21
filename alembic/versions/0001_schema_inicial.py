"""schema inicial

Revision ID: 0001
Revises:
Create Date: 2026-08-20

Tablas del buscador (regiones, comunas, establecimientos, sedes, cursos,
indicadores, actividades, imagenes) + full-text search con `unaccent`.

Notas críticas (ver docs/DATA_DICTIONARY.md):
- `cursos.codigo_curso` es BIGINT: los códigos del MINEDUC son compuestos de
  12 dígitos (ej. 811000000433) y desbordan INTEGER.
- `etiquetas` es TEXT[] (el loader hace split(',') del string CSV del Parquet).
- `distancia` e `id_mongo` se excluyen del schema (artefactos del scrapeo).

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensión unaccent + text search config `spanish_unaccent` ──
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_ts_config WHERE cfgname = 'spanish_unaccent'
            ) THEN
                CREATE TEXT SEARCH CONFIGURATION spanish_unaccent (
                    COPY = pg_catalog.spanish
                );
            END IF;
        END
        $$
        """
    )
    op.execute(
        """
        ALTER TEXT SEARCH CONFIGURATION spanish_unaccent
            ALTER MAPPING FOR hword, hword_part, word
            WITH unaccent, spanish_stem
        """
    )

    # ── Tablas de referencia ──
    op.execute(
        """
        CREATE TABLE regiones (
            codigo INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL UNIQUE
        )
        """
    )

    op.execute(
        """
        CREATE TABLE comunas (
            codigo INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            codigo_region INTEGER NOT NULL REFERENCES regiones(codigo),
            UNIQUE(nombre, codigo_region)
        )
        """
    )
    op.execute("CREATE INDEX idx_comunas_region ON comunas(codigo_region)")

    # ── Establecimientos ──
    # Wrapper IMMUTABLE necesario: `to_tsvector` con config custom (`spanish_unaccent`)
    # es STABLE y PostgreSQL rechaza columnas GENERATED con expresiones no inmutables.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION f_busqueda_tsvector(nombre TEXT, resumen TEXT, etiquetas TEXT[])
        RETURNS tsvector
        LANGUAGE sql
        IMMUTABLE
        AS $$
            SELECT to_tsvector('spanish_unaccent',
                coalesce(nombre, '') || ' ' ||
                coalesce(resumen, '') || ' ' ||
                coalesce(array_to_string(etiquetas, ' '), ''))
        $$
        """
    )
    op.execute(
        """
        CREATE TABLE establecimientos (
            rbd INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            dependencia TEXT NOT NULL,
            telefono TEXT, mail TEXT, url TEXT,
            habilitado_postular BOOLEAN NOT NULL DEFAULT TRUE,
            publicado BOOLEAN NOT NULL DEFAULT FALSE,
            nivel_minimo TEXT, nivel_maximo TEXT,
            director TEXT,
            etiquetas TEXT[],
            resumen_proyecto TEXT,
            documento_proyecto TEXT, documento_reglamento TEXT,
            internado BOOLEAN NOT NULL DEFAULT FALSE,
            integracion BOOLEAN NOT NULL DEFAULT FALSE,
            subvencion_preferencial BOOLEAN NOT NULL DEFAULT FALSE,
            peib BOOLEAN NOT NULL DEFAULT FALSE,
            politica_uniforme TEXT, orientacion_religiosa TEXT,
            alumnos_matriculados INTEGER,
            promedio_alumnos_por_curso FLOAT,
            cantidad_docentes INTEGER,
            regimen TEXT,
            busqueda_tsvector tsvector GENERATED ALWAYS AS (
                f_busqueda_tsvector(nombre, resumen_proyecto, etiquetas)
            ) STORED,
            CONSTRAINT chk_est_alumnos CHECK (
                alumnos_matriculados IS NULL OR alumnos_matriculados >= 0
            ),
            CONSTRAINT chk_est_docentes CHECK (
                cantidad_docentes IS NULL OR cantidad_docentes >= 0
            ),
            CONSTRAINT chk_est_promedio CHECK (
                promedio_alumnos_por_curso IS NULL OR promedio_alumnos_por_curso >= 0
            )
        )
        """
    )
    op.execute("CREATE INDEX idx_est_dep ON establecimientos(dependencia)")
    op.execute("CREATE INDEX idx_est_regimen ON establecimientos(regimen)")
    op.execute("CREATE INDEX idx_est_nivel_max ON establecimientos(nivel_maximo)")
    op.execute("CREATE INDEX idx_est_fts ON establecimientos USING GIN(busqueda_tsvector)")
    op.execute("CREATE INDEX idx_est_etiquetas ON establecimientos USING GIN(etiquetas)")

    # ── Sedes ──
    op.execute(
        """
        CREATE TABLE sedes (
            rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
            codigo_sede INTEGER NOT NULL,
            codigo_region INTEGER NOT NULL REFERENCES regiones(codigo),
            codigo_comuna INTEGER NOT NULL REFERENCES comunas(codigo),
            region TEXT NOT NULL,
            comuna TEXT NOT NULL,
            calle TEXT,
            latitud FLOAT, longitud FLOAT,
            PRIMARY KEY (rbd, codigo_sede),
            CONSTRAINT chk_sede_lat CHECK (latitud IS NULL OR (latitud BETWEEN -90 AND 90)),
            CONSTRAINT chk_sede_lon CHECK (longitud IS NULL OR (longitud BETWEEN -180 AND 180))
        )
        """
    )
    op.execute("CREATE INDEX idx_sedes_comuna ON sedes(codigo_comuna)")

    # ── Cursos ──
    op.execute(
        """
        CREATE TABLE cursos (
            rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
            codigo_curso BIGINT NOT NULL,
            codigo_sede INTEGER NOT NULL,
            glosa_grupo_ensenanza TEXT, glosa_ensenanza TEXT,
            glosa_nivel TEXT, etiqueta_nivel TEXT, sexo TEXT,
            glosa_jornada TEXT, glosa_especialidad TEXT, glosa_grupo_pago TEXT,
            codigo_ensenanza INTEGER, codigo_nivel INTEGER,
            codigo_jornada INTEGER, codigo_sexo INTEGER, codigo_especialidad INTEGER,
            unico_comuna BOOLEAN,
            proporcion_excelencia_transicion FLOAT,
            proporcion_excelencia_regimen FLOAT,
            proporcion_especializacion_temprana FLOAT,
            copago_cuotas INTEGER, copago_valor INTEGER,
            cupos_totales INTEGER,
            vacantes_rango_inferior INTEGER, vacantes_rango_superior INTEGER,
            porcentaje_cambio_inferior FLOAT, porcentaje_cambio_superior FLOAT,
            repitentes_anio_actual INTEGER, repitentes_nivel_anterior INTEGER,
            pre_inscritos_anio_siguiente INTEGER,
            cambios_inferior INTEGER, cambios_superior INTEGER,
            pre_vacantes_inferior INTEGER, pre_vacantes_superior INTEGER,
            rango INTEGER,
            postulantes_anio_anterior INTEGER,
            movimiento_lista_espera_anterior INTEGER,
            PRIMARY KEY (rbd, codigo_curso),
            FOREIGN KEY (rbd, codigo_sede) REFERENCES sedes(rbd, codigo_sede),
            CONSTRAINT chk_curso_copago CHECK (copago_valor IS NULL OR copago_valor >= 0),
            CONSTRAINT chk_curso_cupos CHECK (cupos_totales IS NULL OR cupos_totales >= 0),
            CONSTRAINT chk_curso_pct_inf CHECK (
                porcentaje_cambio_inferior IS NULL
                OR (porcentaje_cambio_inferior >= 0 AND porcentaje_cambio_inferior <= 1)
            ),
            CONSTRAINT chk_curso_pct_sup CHECK (
                porcentaje_cambio_superior IS NULL
                OR (porcentaje_cambio_superior >= 0 AND porcentaje_cambio_superior <= 1)
            )
        )
        """
    )
    op.execute("CREATE INDEX idx_cursos_copago ON cursos(copago_valor)")

    # ── Indicadores (EAV) ──
    op.execute(
        """
        CREATE TABLE indicadores (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
            tipo_indicador TEXT NOT NULL,
            titulo_indicador TEXT, nivel_indicador TEXT,
            descripcion_indicador TEXT,
            nombre_indicador TEXT NOT NULL,
            puntaje FLOAT,
            comparacion_gse_numero INTEGER,
            comparacion_gse_glosa TEXT
        )
        """
    )
    op.execute("CREATE INDEX idx_ind_rbd ON indicadores(rbd)")
    op.execute("CREATE INDEX idx_ind_tipo ON indicadores(tipo_indicador)")

    # ── Actividades ──
    op.execute(
        """
        CREATE TABLE actividades (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
            tipo TEXT, nombre TEXT NOT NULL,
            nivel TEXT, exigencia TEXT
        )
        """
    )
    op.execute("CREATE INDEX idx_act_rbd ON actividades(rbd)")

    # ── Imágenes ──
    op.execute(
        """
        CREATE TABLE imagenes (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
            nombre TEXT,
            url TEXT,
            principal BOOLEAN NOT NULL DEFAULT FALSE
        )
        """
    )
    op.execute("CREATE INDEX idx_img_rbd ON imagenes(rbd)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS imagenes")
    op.execute("DROP TABLE IF EXISTS actividades")
    op.execute("DROP TABLE IF EXISTS indicadores")
    op.execute("DROP TABLE IF EXISTS cursos")
    op.execute("DROP TABLE IF EXISTS sedes")
    op.execute("DROP TABLE IF EXISTS establecimientos")
    op.execute("DROP TABLE IF EXISTS comunas")
    op.execute("DROP TABLE IF EXISTS regiones")
    op.execute("DROP FUNCTION IF EXISTS f_busqueda_tsvector(TEXT, TEXT, TEXT[])")
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS spanish_unaccent")
    op.execute("DROP EXTENSION IF EXISTS unaccent")
