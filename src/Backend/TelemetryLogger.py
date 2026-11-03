import os
import csv
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from Backend.TelemetryTypes import TelemetrySnapshot


class TelemetryLogger:
    """Bounded, persistent session telemetry logger writing RFC 4180 CSV files.
    
    Adheres to safety invariant INV-1: all I/O is fail-safe and completely insulated
    so disk write failures can never interrupt GUI operation or safety trip mechanisms.
    """
    MAX_FILE_BYTES = 10 * 1024 * 1024  # Strict 10 MB ceiling per session log
    MAX_RETAINED_SESSIONS = 5          # Keep at most 5 recent sessions, prune older
    CSV_HEADER = [
        "timestamp_unix",
        "iso_datetime",
        "cpu_temp_c",
        "gpu_temp_c",
        "cpu_fan_rpm",
        "gpu_fan_rpm",
        "mode",
        "ac_power"
    ]

    def __init__(self, logDir: Optional[Path] = None, enabled: bool = True) -> None:
        if logDir is None:
            base = os.environ.get('LOCALAPPDATA', tempfile.gettempdir())
            self.logDir = Path(base) / 'tcc-g15' / 'telemetry'
        else:
            self.logDir = Path(logDir)

        self.enabled = enabled
        self._currentFile = None
        self._writer = None
        self._currentFilePath: Optional[Path] = None
        self._bytesWritten = 0

        if self.enabled:
            self._init_session()

    def _init_session(self) -> None:
        try:
            self.logDir.mkdir(parents=True, exist_ok=True)
            self._prune_old_sessions()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._currentFilePath = self.logDir / f"session_{timestamp}.csv"

            self._currentFile = open(self._currentFilePath, "w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._currentFile)
            self._writer.writerow(self.CSV_HEADER)
            self._currentFile.flush()
            self._bytesWritten = self._currentFilePath.stat().st_size
        except Exception:
            self._currentFile = None
            self._writer = None

    def _prune_old_sessions(self) -> None:
        try:
            csv_files = sorted(self.logDir.glob("session_*.csv"), key=os.path.getmtime)
            while len(csv_files) >= self.MAX_RETAINED_SESSIONS:
                oldest = csv_files.pop(0)
                try:
                    oldest.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            pass

    def log(self, snapshot: TelemetrySnapshot, mode: str) -> bool:
        """Writes a single telemetry row to the active session CSV."""
        if not self.enabled or self._writer is None or self._currentFile is None:
            return False

        if self._bytesWritten >= self.MAX_FILE_BYTES:
            return False  # Bounded size limit reached

        try:
            ts = snapshot.timestamp if snapshot.timestamp > 0 else datetime.now().timestamp()
            iso_now = datetime.fromtimestamp(ts).isoformat(timespec='seconds')
            row = [
                f"{ts:.2f}",
                iso_now,
                snapshot.cpu_temp if snapshot.cpu_temp is not None else "",
                snapshot.gpu_temp if snapshot.gpu_temp is not None else "",
                snapshot.cpu_rpm if snapshot.cpu_rpm is not None else "",
                snapshot.gpu_rpm if snapshot.gpu_rpm is not None else "",
                mode,
                "AC" if snapshot.is_ac_power is True else ("Battery" if snapshot.is_ac_power is False else "Unknown")
            ]
            self._writer.writerow(row)
            self._currentFile.flush()
            self._bytesWritten = self._currentFilePath.stat().st_size
            return True
        except Exception:
            return False

    def set_enabled(self, enabled: bool) -> None:
        """Toggles logging state dynamically; flushes on disable, creates new session on enable."""
        if self.enabled == enabled:
            return
        self.enabled = enabled
        if self.enabled:
            if self._currentFile is None:
                self._init_session()
        else:
            self.close()

    def close(self) -> None:
        """Flushes and closes the open session log file."""
        if self._currentFile is not None:
            try:
                self._currentFile.flush()
                self._currentFile.close()
            except Exception:
                pass
            self._currentFile = None
            self._writer = None

    @property
    def current_log_path(self) -> Optional[Path]:
        return self._currentFilePath if (self._currentFilePath and self._currentFilePath.exists()) else None

    @classmethod
    def get_recent_logs(cls, logDir: Optional[Path] = None) -> List[Path]:
        """Returns sorted list of available session CSV files (most recent first)."""
        if logDir is None:
            base = os.environ.get('LOCALAPPDATA', tempfile.gettempdir())
            target = Path(base) / 'tcc-g15' / 'telemetry'
        else:
            target = Path(logDir)

        if not target.is_dir():
            return []
        try:
            return sorted(target.glob("session_*.csv"), key=os.path.getmtime, reverse=True)
        except Exception:
            return []
