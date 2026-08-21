"""Smoke test de la API en vivo (sin pytest): valida endpoints clave.

Uso:
    python scripts/validate_api.py [base_url]

Levanta la app con TestClient y verifica que los endpoints principales respondan
correctamente (health, stats, search FTS, ficha, compare, errores).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from src.api.main import app

CHECKS: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok))
    status = "OK" if ok else "FAIL"
    suffix = f" — {detail}" if detail and not ok else ""
    print(f"  [{status}] {name}{suffix}")


def main() -> int:
    print("Validando API...")
    with TestClient(app) as c:
        r = c.get("/api/v1/health")
        check("GET /health", r.status_code == 200 and r.json()["status"] == "ok")

        r = c.get("/api/v1/stats")
        body = r.json()
        check("GET /stats", r.status_code == 200 and body["establecimientos"] > 0)

        r = c.get("/api/v1/search", params={"q": "aleman", "limit": 5})
        check("GET /search?q=aleman (FTS unaccent)", r.status_code == 200 and r.json()["total"] > 0)

        r = c.get("/api/v1/search", params={"limit": 3})
        check("GET /search sin q (paginado)", r.status_code == 200 and len(r.json()["results"]) == 3)

        r = c.get("/api/v1/search", params={"limit": 1000})
        check("GET /search limit=1000 → 400", r.status_code == 400)

        r = c.get("/api/v1/establecimientos/60")
        check("GET /establecimientos/60 (ficha)", r.status_code == 200 and "sedes" in r.json())

        r = c.get("/api/v1/establecimientos/99999999")
        check("GET /establecimientos/99999999 → 404", r.status_code == 404)

        r = c.get("/api/v1/compare", params={"rbds": "60,22248"})
        check("GET /compare?rbds=60,22248", r.status_code == 200 and len(r.json()["establecimientos"]) == 2)

        r = c.get("/api/v1/compare", params={"rbds": "1,2,3,4,5,6,7,8,9,10,11"})
        check("GET /compare con 11 RBDs → 400", r.status_code == 400)

    failed = [name for name, ok in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks pasaron.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
