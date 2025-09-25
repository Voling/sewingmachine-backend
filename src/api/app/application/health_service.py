from __future__ import annotations

import datetime
from typing import Dict

from ..config.settings import HealthSettings


class HealthService:
    def __init__(self, settings: HealthSettings) -> None:
        self._settings = settings

    def execute(self) -> Dict[str, object]:
        return {
            "status": "ok",
            "service": self._settings.service_name,
            "time": datetime.datetime.utcnow().isoformat() + "Z",
        }
