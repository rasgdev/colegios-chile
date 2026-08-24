"""Tests de la configuración CORS en src/api/main.py."""
from __future__ import annotations

from src.api import main


def test_cors_development_sin_origenes_explicitos(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "cors_origins", "")
    monkeypatch.setattr(main.settings, "environment", "development")
    assert main._get_cors_origins() == [
        "http://localhost:4321",
        "http://127.0.0.1:4321",
    ]


def test_cors_production_sin_origenes_queda_vacio(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "cors_origins", "")
    monkeypatch.setattr(main.settings, "environment", "production")
    assert main._get_cors_origins() == []


def test_cors_origenes_explicitos_csv(monkeypatch) -> None:
    monkeypatch.setattr(
        main.settings,
        "cors_origins",
        "https://a.cl, https://b.cl",
    )
    monkeypatch.setattr(main.settings, "environment", "production")
    assert main._get_cors_origins() == ["https://a.cl", "https://b.cl"]
