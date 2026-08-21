"""Tests de la API (requieren PostgreSQL con datos cargados)."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.usefixtures("client")


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_regiones(client):
    r = client.get("/api/v1/regiones")
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 16
    assert all({"codigo", "nombre"} <= set(x) for x in body)
    assert "max-age=86400" in r.headers.get("Cache-Control", "")


def test_comunas_por_region_cascada(client):
    r = client.get("/api/v1/comunas", params={"region": 13})
    assert r.status_code == 200
    body = r.json()
    assert body  # Metropolitana tiene comunas
    assert all(c["codigo_region"] == 13 for c in body)


def test_comunas_requiere_region(client):
    r = client.get("/api/v1/comunas")
    assert r.status_code == 400


def test_stats(client):
    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    assert r.json()["establecimientos"] > 0


def test_search_sin_q_paginado(client):
    r = client.get("/api/v1/search", params={"limit": 3})
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) == 3
    assert body["total"] >= 3


def test_search_fts_unaccent_aleman(client):
    r = client.get("/api/v1/search", params={"q": "aleman", "limit": 10})
    assert r.status_code == 200
    nombres = [x["nombre"] for x in r.json()["results"]]
    assert any("ALEMAN" in n.upper() for n in nombres)


def test_search_limit_sobre_maximo_400(client):
    r = client.get("/api/v1/search", params={"limit": 1000})
    assert r.status_code == 400


def test_search_filtro_dependencia(client):
    r = client.get("/api/v1/search", params={"dependencia": "PUBLICO", "limit": 5})
    assert r.status_code == 200
    assert all(x["dependencia"] == "PUBLICO" for x in r.json()["results"])


def test_search_filtro_nivel_media(client):
    r = client.get("/api/v1/search", params={"nivel": "MEDIA", "limit": 5})
    assert r.status_code == 200
    assert r.json()["total"] > 0


def test_search_filtro_regimen_case_insensitive(client):
    r = client.get("/api/v1/search", params={"regimen": "mixto", "limit": 5})
    assert r.status_code == 200
    assert r.json()["total"] > 0


def test_search_copago_sin_duplicados(client):
    r = client.get("/api/v1/search", params={"copago_max": 50000, "limit": 100})
    assert r.status_code == 200
    rbds = [x["rbd"] for x in r.json()["results"]]
    assert len(rbds) == len(set(rbds))


def test_ficha_completa(client):
    r = client.get("/api/v1/establecimientos/60")
    assert r.status_code == 200
    body = r.json()
    assert body["establecimiento"]["rbd"] == 60
    for key in ("sedes", "cursos_resumen", "indicadores", "actividades", "imagenes"):
        assert key in body


def test_ficha_rbd_inexistente_404(client):
    r = client.get("/api/v1/establecimientos/99999999")
    assert r.status_code == 404
    assert r.json()["error"] == "establecimiento_no_encontrado"


def test_subrecurso_rbd_inexistente_404(client):
    r = client.get("/api/v1/indicadores", params={"rbd": 99999999})
    assert r.status_code == 404


def test_compare_ok(client):
    r = client.get("/api/v1/compare", params={"rbds": "60,22248"})
    assert r.status_code == 200
    assert [e["rbd"] for e in r.json()["establecimientos"]] == [60, 22248]


def test_compare_mas_de_10_400(client):
    rbds = ",".join(str(i) for i in range(1, 12))
    r = client.get("/api/v1/compare", params={"rbds": rbds})
    assert r.status_code == 400
    assert r.json()["error"] == "demasiados_colegios"


def test_compare_rbd_inexistente_404(client):
    r = client.get("/api/v1/compare", params={"rbds": "60,99999999"})
    assert r.status_code == 404
    assert r.json()["error"] == "colegios_no_encontrados"
