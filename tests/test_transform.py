import json
from pathlib import Path

import pytest
from etl.transform.models import EstablecimientoDetalle
from etl.transform.normalizers import (
    construir_actividades,
    construir_cursos,
    construir_establecimientos,
    construir_imagenes,
    construir_indicadores,
    construir_sedes,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def detalle_8997() -> EstablecimientoDetalle:
    path = FIXTURES_DIR / "detalle_8997.json"
    data = json.loads(path.read_text())
    return EstablecimientoDetalle.model_validate(data)


class TestValidarModelos:
    def test_detalle_8997_valido(self, detalle_8997):
        assert detalle_8997.rbd == 8997
        assert detalle_8997.nombre is not None
        assert len(detalle_8997.sedes) > 0

    def test_comuna_recoleta_valida(self):
        path = FIXTURES_DIR / "comuna_recoleta.json"
        data = json.loads(path.read_text())
        assert isinstance(data, list)
        assert len(data) > 0
        for item in data:
            assert "rbd" in item


class TestConstruirDataFrames:
    def test_establecimientos_no_vacio(self, detalle_8997):
        df = construir_establecimientos([detalle_8997])
        assert len(df) == 1
        assert df["rbd"][0] == 8997

    def test_sedes_no_vacio(self, detalle_8997):
        df = construir_sedes([detalle_8997])
        assert len(df) > 0
        assert "codigo_sede" in df.columns
        assert "rbd" in df.columns

    def test_cursos_no_vacio(self, detalle_8997):
        df = construir_cursos([detalle_8997])
        assert len(df) > 0
        assert "codigo_curso" in df.columns
        assert "rbd" in df.columns
        assert "codigo_sede" in df.columns

    def test_actividades_no_vacio(self, detalle_8997):
        df = construir_actividades([detalle_8997])
        assert len(df) > 0
        assert "tipo" in df.columns

    def test_indicadores_no_vacio(self, detalle_8997):
        df = construir_indicadores([detalle_8997])
        assert len(df) > 0
        assert "nombre_indicador" in df.columns

    def test_imagenes_no_vacio(self, detalle_8997):
        df = construir_imagenes([detalle_8997])
        assert len(df) > 0
        assert "principal" in df.columns
