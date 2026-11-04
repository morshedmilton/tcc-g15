"""ProcessMonitorWorker: Secondary QThread worker for non-invasive process scanning.

Executes psutil.process_iter(['name']) on a dedicated worker thread decoupled from
the PySide6 GUI thread, emitting lowercase process names via Qt Queued Signals (DEF-009).
Strictly queries NT kernel table metadata without opening handles or reading memory (REQ-0601).
"""
from __future__ import annotations

import logging
from typing import Optional, Set
from PySide6 import QtCore
import psutil

logger = logging.getLogger("tcc-g15")


class ProcessMonitorWorker(QtCore.QObject):
    """Secondary thread worker polling running processes non-invasively at 2500ms intervals."""

    processes_scanned = QtCore.Signal(set)

    def __init__(self, interval_ms: int = 2500, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._interval_ms = interval_ms
        self._timer: Optional[QtCore.QTimer] = None
        self._running = False

    @QtCore.Slot()
    def start(self) -> None:
        """Start the periodic process scanning timer on the worker thread."""
        self._running = True
        if self._timer is None:
            self._timer = QtCore.QTimer(self)
            self._timer.setInterval(self._interval_ms)
            self._timer.timeout.connect(self._on_timer_tick)
        if not self._timer.isActive():
            self._timer.start()

        # Immediate first scan on thread startup
        self._on_timer_tick()

    @QtCore.Slot()
    def stop(self) -> None:
        """Stop periodic scanning and deactivate the timer."""
        self._running = False
        if self._timer is not None and QtCore.QThread.currentThread() == self.thread():
            try:
                if self._timer.isActive():
                    self._timer.stop()
            except Exception:
                pass

    def setInterval(self, ms: int) -> None:
        """Update polling interval in milliseconds."""
        self._interval_ms = ms
        if self._timer is not None:
            self._timer.setInterval(ms)

    def scan_once(self) -> Set[str]:
        """Perform a single non-invasive enumeration of process names via NT kernel tables.

        Guarantees zero memory inspection and zero OpenProcess handles to ensure 100%
        transparency with anti-cheat software (BattlEye, Vanguard, Easy Anti-Cheat).
        """
        active_processes: Set[str] = set()
        try:
            for proc in psutil.process_iter(["name"]):
                try:
                    info = proc.info
                    name = info.get("name") if info else None
                    if name:
                        active_processes.add(name.strip().lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as ex:
                    logger.debug("Transient process enumeration exception: %s", ex)
                    continue
        except Exception as ex:
            logger.warning("psutil.process_iter failed: %s", ex)
        return active_processes

    def _on_timer_tick(self) -> None:
        if not self._running:
            return
        active_set = self.scan_once()
        self.processes_scanned.emit(active_set)
