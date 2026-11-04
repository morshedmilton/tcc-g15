"""ProcessRulePresets: Curated default rules catalog for popular games and creator apps.

Implements REQ-0604 / SRC-009 with 18 verified presets across AAA Gaming,
Competitive Esports, and Content Creation / Benchmarking.
"""
from __future__ import annotations

from typing import List
from Backend.ProcessRule import ProcessRule


def get_default_presets() -> List[ProcessRule]:
    """Return the 18 curated default ProcessRule presets matching SRC-009 and REQ-0604."""
    return [
        # AAA Gaming
        ProcessRule(
            process_name="cyberpunk2077.exe",
            target_mode="G_Mode",
            enabled=True,
            description="Cyberpunk 2077",
        ),
        ProcessRule(
            process_name="gta5.exe",
            target_mode="Auto",
            enabled=True,
            description="Grand Theft Auto V",
        ),
        ProcessRule(
            process_name="rdr2.exe",
            target_mode="G_Mode",
            enabled=True,
            description="Red Dead Redemption 2",
        ),
        ProcessRule(
            process_name="eldenring.exe",
            target_mode="Auto",
            enabled=True,
            description="Elden Ring",
        ),
        ProcessRule(
            process_name="bg3.exe",
            target_mode="Auto",
            enabled=True,
            description="Baldur's Gate 3",
        ),
        # Competitive Esports
        ProcessRule(
            process_name="cs2.exe",
            target_mode="Auto",
            enabled=True,
            description="Counter-Strike 2",
        ),
        ProcessRule(
            process_name="r5apex.exe",
            target_mode="Auto",
            enabled=True,
            description="Apex Legends",
        ),
        ProcessRule(
            process_name="valorant-win64-shipping.exe",
            target_mode="Auto",
            enabled=True,
            description="Valorant",
        ),
        ProcessRule(
            process_name="fortniteclient-win64-shipping.exe",
            target_mode="Auto",
            enabled=True,
            description="Fortnite",
        ),
        ProcessRule(
            process_name="overwatch.exe",
            target_mode="Auto",
            enabled=True,
            description="Overwatch 2",
        ),
        ProcessRule(
            process_name="cod.exe",
            target_mode="G_Mode",
            enabled=True,
            description="Call of Duty: Warzone / MW",
        ),
        # Content Creation & Benchmarking
        ProcessRule(
            process_name="blender.exe",
            target_mode="Auto",
            enabled=True,
            description="Blender 3D",
        ),
        ProcessRule(
            process_name="premiere.exe",
            target_mode="Auto",
            enabled=True,
            description="Adobe Premiere Pro",
        ),
        ProcessRule(
            process_name="afterfx.exe",
            target_mode="Auto",
            enabled=True,
            description="Adobe After Effects",
        ),
        ProcessRule(
            process_name="resolve.exe",
            target_mode="Auto",
            enabled=True,
            description="DaVinci Resolve",
        ),
        ProcessRule(
            process_name="handbrake.exe",
            target_mode="Auto",
            enabled=True,
            description="HandBrake",
        ),
        ProcessRule(
            process_name="cinebench.exe",
            target_mode="G_Mode",
            enabled=True,
            description="Cinebench",
        ),
        ProcessRule(
            process_name="3dmark.exe",
            target_mode="G_Mode",
            enabled=True,
            description="3DMark",
        ),
    ]
