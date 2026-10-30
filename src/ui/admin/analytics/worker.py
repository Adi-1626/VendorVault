"""Background loading for the Analytics page (keeps the UI responsive)."""
from __future__ import annotations

import traceback
from datetime import date
from typing import Optional, Tuple

from PySide6.QtCore import QObject, QRunnable, Signal

from src.logic.analytics_engine import build_snapshot


class SnapshotSignals(QObject):
    done = Signal(int, object)      # (request id, Snapshot)
    failed = Signal(int, str)


class SnapshotJob(QRunnable):
    """Builds a :class:`Snapshot` on a pool thread. The engine opens its own
    SQLite connection per query, so this is safe off the UI thread."""

    def __init__(self, request_id: int, preset: str, custom: Optional[Tuple[date, date]]):
        super().__init__()
        self.setAutoDelete(False)    # the page keeps a reference until it reports back
        self.request_id = request_id
        self.preset = preset
        self.custom = custom
        self.signals = SnapshotSignals()

    def run(self) -> None:
        try:
            snap = build_snapshot(self.preset, self.custom)
        except Exception:  # noqa: BLE001
            self.signals.failed.emit(self.request_id, traceback.format_exc())
            return
        self.signals.done.emit(self.request_id, snap)
