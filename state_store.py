from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path


logger = logging.getLogger(__name__)


class AlertStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.data: dict[str, float] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.data = {str(key): float(value) for key, value in raw.items()}
        except Exception as exc:
            logger.warning("تعذر قراءة ملف الحالة %s: %s", self.path, exc)
            self.data = {}

    def can_send(self, key: str, cooldown_hours: float) -> bool:
        if cooldown_hours <= 0:
            return True
        last_sent = self.data.get(key)
        if last_sent is None:
            return True
        return (time.time() - last_sent) >= cooldown_hours * 3600

    def mark_sent(self, key: str) -> None:
        with self.lock:
            self.data[key] = time.time()
            self._save_atomic()

    def _save_atomic(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
                json.dump(self.data, file, ensure_ascii=False, indent=2)
            os.replace(temporary_path, self.path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
