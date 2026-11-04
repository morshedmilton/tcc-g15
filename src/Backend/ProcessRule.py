"""ProcessRule: Data model for process-aware thermal profile switching.

Encapsulates application executable matching, target thermal profile assignment,
cooling severity priority arbitration, and JSON serialization.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger("tcc-g15")


def _as_bool(value: Any) -> bool:
    """JSON stores booleans, but hand-edited configs use "false"/"0"/"no".

    bool("false") is True, so a naive cast silently enables a rule the user disabled
    (DEF-708).
    """
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "off")
    return bool(value)


# Cooling Severity Priority Matrix (ADR-006 / PRD REQ-0602):
# G_Mode (0xAB) > Performance (0xA1) > Custom (0x00) > Balanced (0xA0) > Quiet (0xA3)
# Auto is adaptive: it can reach full speed, so it ranks with the old Performance slot.
# Without an entry here an Auto rule sorted below Balanced and lost arbitration (DEF-704).
COOLING_SEVERITY_ORDER: Dict[str, int] = {
    "G_Mode": 5,
    "Performance": 4,
    "Auto": 4,
    "Custom": 3,
    "Balanced": 2,
    "Quiet": 1,
}

# The profiles a rule may target. They must exist as buttons in the window, otherwise a
# rule could put the firmware in a mode the UI cannot display (silent lie). Older rules
# and presets may name Performance/Quiet; they are coerced to the nearest visible profile
# with the intent preserved: Performance -> Auto (adaptive cooling), Quiet -> Balanced.
VISIBLE_PROFILES = ("Auto", "Balanced", "G_Mode", "Custom")
LEGACY_TARGET_MAP: Dict[str, str] = {"Performance": "Auto", "Quiet": "Balanced"}


@dataclass
class ProcessRule:
    """A thermal switching rule mapped to a process executable name.

    Attributes:
        process_name: Normalized lowercase executable basename, e.g. "cs2.exe".
        target_mode: Target Alienware thermal mode name, e.g. "Performance", "G_Mode".
        enabled: Whether this rule actively triggers automatic profile switching.
        description: Human-readable application title or description.
    """

    process_name: str
    target_mode: str
    enabled: bool = True
    description: str = ""

    def __post_init__(self) -> None:
        self.process_name = self.normalize_process_name(self.process_name)
        # Normalize target mode if formatted with spaces (e.g. "G Mode" -> "G_Mode")
        if self.target_mode:
            normalized_mode = self.target_mode.strip()
            if normalized_mode.lower() in ("g mode", "g-mode", "g_mode"):
                normalized_mode = "G_Mode"
            self.target_mode = normalized_mode

    @staticmethod
    def normalize_process_name(name: str) -> str:
        """Strip directory paths, whitespace, enforce lowercase and .exe extension."""
        if not name:
            return ""
        cleaned = os.path.basename(name).strip().lower()
        if cleaned and not cleaned.endswith(".exe"):
            cleaned = f"{cleaned}.exe"
        return cleaned

    @property
    def cooling_priority(self) -> int:
        """Return integer cooling severity rank (higher value = stronger cooling)."""
        return COOLING_SEVERITY_ORDER.get(self.target_mode, 0)

    def matches(self, scanned_name: str) -> bool:
        """Check if a scanned process name matches this rule.

        Supports standard executable matching and official aliases
        (e.g. bg3.exe <-> bg3_dx11.exe).
        """
        if not scanned_name:
            return False
        clean = os.path.basename(scanned_name).strip().lower()
        if clean == self.process_name:
            return True
        # Alias matching for Baldur's Gate 3 Vulkan vs DirectX 11 (SRC-009 / REQ-0604)
        if self.process_name == "bg3.exe" and clean == "bg3_dx11.exe":
            return True
        if self.process_name == "bg3_dx11.exe" and clean == "bg3.exe":
            return True
        return False

    def with_visible_target(self) -> "ProcessRule":
        """Return a copy whose target is one of the four offered profiles.

        Used when loading persisted rules: an old config may name Performance/Quiet, which
        are no longer shown in the window. Coercing at load time keeps the stored file
        untouched while guaranteeing the UI can display the active profile.
        """
        if self.target_mode in VISIBLE_PROFILES:
            return self
        coerced = LEGACY_TARGET_MAP.get(self.target_mode, "Balanced")
        logger.info("Rule %s target %r -> %r", self.process_name, self.target_mode, coerced)
        return ProcessRule(self.process_name, coerced, self.enabled, self.description)

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, ProcessRule):
            return NotImplemented
        return self.cooling_priority < other.cooling_priority

    def __le__(self, other: Any) -> bool:
        if not isinstance(other, ProcessRule):
            return NotImplemented
        return self.cooling_priority <= other.cooling_priority

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, ProcessRule):
            return NotImplemented
        return self.cooling_priority > other.cooling_priority

    def __ge__(self, other: Any) -> bool:
        if not isinstance(other, ProcessRule):
            return NotImplemented
        return self.cooling_priority >= other.cooling_priority

    def to_dict(self) -> Dict[str, Any]:
        """Serialize rule configuration to dictionary for JSON persistence."""
        return {
            "process_name": self.process_name,
            "target_mode": self.target_mode,
            "enabled": self.enabled,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProcessRule:
        """Deserialize rule configuration from dictionary."""
        return cls(
            process_name=str(data.get("process_name", "")),
            target_mode=str(data.get("target_mode", "Balanced")),
            enabled=_as_bool(data.get("enabled", True)),
            description=str(data.get("description", "")),
        )
