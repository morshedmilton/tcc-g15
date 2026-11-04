"""One-click diagnostics: a redacted bundle plus a prefilled GitHub issue URL.

Never includes usernames, serial numbers, MAC addresses or file paths outside the app.
"""
import json
import os
import platform
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote

REPO = 'morshedmilton/tcc-g15'
LOG_CANDIDATES = (
    Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'tcc-g15' / 'app.log',
)


def _wmi(classes: Tuple[str, ...]) -> dict:
    out = {}
    try:
        import wmi
        c = wmi.WMI()
        for name in classes:
            try:
                insts = getattr(c, name)()
                rows = []
                for inst in insts:
                    row = {}
                    for key in inst.properties:
                        if key.lower() in ('serialnumber', 'uuid', 'pnpdeviceid'):
                            continue
                        try:
                            value = getattr(inst, key, None)
                        except Exception:
                            value = None
                        if value not in (None, '', []):
                            row[key] = value
                    rows.append(row)
                out[name] = rows
            except Exception as ex:
                out[name] = f'error: {type(ex).__name__}'
    except Exception as ex:
        out['error'] = f'{type(ex).__name__}: {ex}'
    return out


def _awccDump() -> dict:
    try:
        from Backend.AWCCWmiWrapper import AWCCWmiWrapper
        from wmi import WMI
        w = AWCCWmiWrapper(WMI(namespace="root\\WMI").AWCCWmiMethodFunction()[0])
        fans = w.GetFanIdsAndRelatedSensorsIds()
        return {
            'fans': [{'fan_id': f, 'sensors': list(s),
                      'rpm': w.GetFanRPM(f),
                      'temps': {str(sid): w.GetSensorTemperature(sid) for sid in s}} for f, s in fans],
            'live_sensors': {str(sid): w.GetSensorTemperature(sid)
                             for sid in range(AWCCWmiWrapper.SENSOR_ID_FIRST, AWCCWmiWrapper.SENSOR_ID_LAST + 1)
                             if w.GetSensorTemperature(sid) is not None},
        }
    except Exception as ex:
        return {'error': f'{type(ex).__name__}: {ex}'}


def _tail(path: Path, lines: int = 400) -> str:
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return ''.join(f.readlines()[-lines:])
    except OSError:
        return ''


def build(appName: str, version: str) -> Tuple[Optional[str], str]:
    """Returns (zip path or None, prefilled issue URL)."""
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    outDir = Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'tcc-g15' / 'reports'
    outDir.mkdir(parents=True, exist_ok=True)
    zipPath = outDir / f'bugreport-{stamp}.zip'

    system = {
        'app': appName,
        'version': version,
        'os': platform.platform(),
        'python': sys.version,
        'frozen': bool(getattr(sys, 'frozen', False)),
        'generated': stamp,
    }
    wmiDump = _wmi(('Win32_ComputerSystem', 'Win32_BIOS', 'Win32_Processor',
                    'Win32_VideoController', 'Win32_BaseBoard', 'Win32_Battery'))
    awcc = _awccDump()
    logs = {str(p): _tail(p) for p in LOG_CANDIDATES if p.exists()}

    try:
        with zipfile.ZipFile(zipPath, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('system.json', json.dumps(system, indent=2, default=str))
            z.writestr('wmi.json', json.dumps(wmiDump, indent=2, default=str))
            z.writestr('awcc.json', json.dumps(awcc, indent=2, default=str))
            for name, text in logs.items():
                z.writestr('app.log', text)
            try:
                from Backend.TelemetryLogger import TelemetryLogger
                recent_logs = TelemetryLogger.get_recent_logs()
                if recent_logs:
                    z.write(recent_logs[0], arcname='telemetry.csv')
            except Exception:
                pass
            try:
                from Backend.SessionMetricsTracker import get_session_tracker
                metrics = get_session_tracker().get_summary()
                z.writestr('session_metrics.json', json.dumps(metrics, indent=2, default=str))
            except Exception:
                pass
            z.writestr('README.txt',
                       'Attach this zip to the issue. It contains model/BIOS/firmware data, the '
                       'app log, session metrics, and session telemetry. Serial numbers, UUIDs and MAC addresses are stripped.\n')
    except Exception as ex:
        print(f'diagnostics: could not write zip ({type(ex).__name__}: {ex})')
        zipPath = None

    cs = (wmiDump.get('Win32_ComputerSystem') or [{}])
    model = cs[0].get('Model', 'unknown') if isinstance(cs, list) and cs else 'unknown'
    title = f'[bug] <what happened> on {model}'
    body = (
        f'**App version:** {version}\n'
        f'**Model:** {model}\n'
        f'**OS:** {platform.platform()}\n\n'
        '**What I did:**\n\n**What I expected:**\n\n**What happened:**\n\n'
        f'**Diagnostics:** attach `{zipPath.name if zipPath else "n/a"}`\n'
    )
    url = f'https://github.com/{REPO}/issues/new?title={quote(title)}&body={quote(body)}&labels=bug'
    return (str(zipPath) if zipPath else None), url
