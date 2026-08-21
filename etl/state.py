import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import settings


class ETLState:
    def __init__(self) -> None:
        self.comunas_procesadas: dict[str, str] = {}
        self.rbds_descargados: dict[str, str] = {}
        self._file: Path = settings.state_file

    def comuna_esta_procesada(self, comuna: str) -> bool:
        return comuna in self.comunas_procesadas

    def rbd_esta_descargado(self, rbd: int | str) -> bool:
        return str(rbd) in self.rbds_descargados

    def marcar_comuna(self, comuna: str) -> None:
        self.comunas_procesadas[comuna] = datetime.now(timezone.utc).isoformat()

    def marcar_rbd(self, rbd: int) -> None:
        self.rbds_descargados[str(rbd)] = datetime.now(timezone.utc).isoformat()

    def marcar_rbd_fallido(self, rbd: int) -> None:
        pass

    @property
    def total_comunas(self) -> int:
        return len(self.comunas_procesadas)

    @property
    def total_rbds(self) -> int:
        return len(self.rbds_descargados)

    def rbds_pendientes(self, todos_los_rbds: set[str]) -> set[str]:
        return todos_los_rbds - set(self.rbds_descargados.keys())

    def guardar(self) -> None:
        data: dict[str, Any] = {
            "comunas_procesadas": self.comunas_procesadas,
            "rbds_descargados": self.rbds_descargados,
        }
        self._file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._file.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self._file)
        except Exception:
            os.unlink(tmp)
            raise

    @classmethod
    def cargar(cls) -> "ETLState":
        state = cls()
        if state._file.exists():
            data = json.loads(state._file.read_text())
            state.comunas_procesadas = data.get("comunas_procesadas", {})
            state.rbds_descargados = data.get("rbds_descargados", {})
        return state
