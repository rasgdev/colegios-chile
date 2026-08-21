"""Tests de las constantes de dominio (niveles y entidades)."""
from src.domain.entities import (
    CATEGORIAS_NIVEL,
    NIVELES_ORDENADOS,
    NIVELES_VALIDOS,
    Establecimiento,
    rango_indices_categoria,
)


def test_niveles_ordenados_cubren_categorias():
    grados_en_categorias = {g for grados in CATEGORIAS_NIVEL.values() for g in grados}
    assert grados_en_categorias == set(NIVELES_ORDENADOS)


def test_rango_indices_parvulario():
    assert rango_indices_categoria("PARVULARIO") == (0, 1)


def test_rango_indices_media():
    # I Medio (10) .. IV Medio (13)
    assert rango_indices_categoria("MEDIA") == (10, 13)


def test_rango_indices_basica():
    assert rango_indices_categoria("BASICA") == (2, 9)


def test_niveles_validos():
    assert set(NIVELES_VALIDOS) == {"PARVULARIO", "BASICA", "MEDIA"}


def test_establecimiento_etiquetas_default():
    e = Establecimiento(rbd=1, nombre="X", dependencia="PUBLICO")
    assert e.etiquetas == []
    assert e.regimen is None
