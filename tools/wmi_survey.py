"""Read-only WMI capability survey for the Dell G15 5530.
Enumerates every namespace/class that could matter for thermal/fan/power/lighting.
Writes docs/WMI_MAP.json. Changes nothing, needs no admin for most classes."""
import json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "WMI_MAP.json"

# Classes worth probing, grouped by capability
PROBES = {
    "thermal_fan": [
        ("root\\WMI", "AWCCWmiMethodFunction"),
        ("root\\WMI", "MSAcpi_ThermalZoneTemperature"),
        ("root\\WMI", "KernelThermalPolicyChange"),
        ("root\\WMI", "KernelThermalConstraintChange"),
    ],
    "power": [
        ("root\\WMI", "BatteryStatus"),
        ("root\\CIMV2", "Win32_Battery"),
        ("root\\CIMV2", "Win32_PowerPlan"),
        ("root\\CIMV2", "Win32_ComputerSystem"),
    ],
    "processor_gpu": [
        ("root\\CIMV2", "Win32_Processor"),
        ("root\\CIMV2", "Win32_VideoController"),
        ("root\\CIMV2", "Win32_Fan"),
        ("root\\CIMV2", "Win32_TemperatureProbe"),
    ],
    "lighting": [
        ("root\\WMI", "AWCCWmiMethodFunction"),   # ReadChassisColor / ReadTotalofGPIOs
        ("root\\CIMV2", "Win32_Keyboard"),
    ],
    "system": [
        ("root\\CIMV2", "Win32_BIOS"),
        ("root\\CIMV2", "Win32_BaseBoard"),
        ("root\\CIMV2", "Win32_PhysicalMemory"),
    ],
}


def probe(namespace: str, cls: str) -> dict:
    out = {"namespace": namespace, "class": cls, "exists": False, "instances": 0, "methods": [], "error": None}
    try:
        import wmi
        c = wmi.WMI(namespace=namespace)
        # class existence + method list
        klass = getattr(c, cls, None)
        if klass is None:
            out["error"] = "class not found"
            return out
        out["exists"] = True
        try:
            insts = klass()
            out["instances"] = len(insts)
        except Exception as ex:
            out["instances"] = 0
            out["error"] = f"instance query: {type(ex).__name__}"
    except Exception as ex:
        out["error"] = f"{type(ex).__name__}: {ex}"
    return out


def awcc_methods() -> list:
    """Method ids on the AWCC class, read from the CIM schema (no instance needed)."""
    try:
        import win32com.client
        loc = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        svc = loc.ConnectServer(".", "root\\WMI")
        klass = svc.Get("AWCCWmiMethodFunction")
        out = []
        for m in klass.Methods_:
            try:
                out.append({"name": m.Name, "id": m.Qualifiers_("WmiMethodId").Value if m.Qualifiers_("WmiMethodId") else None})
            except Exception:
                out.append({"name": m.Name, "id": None})
        return out
    except Exception as ex:
        return [{"error": f"{type(ex).__name__}: {ex}"}]


def main():
    report = {"model": None, "bios": None, "groups": {}}
    try:
        import wmi
        c = wmi.WMI()
        cs = c.Win32_ComputerSystem()[0]
        report["model"] = f"{cs.Manufacturer} {cs.Model}".strip()
        bios = c.Win32_BIOS()[0]
        report["bios"] = {"version": bios.SMBIOSBIOSVersion, "release": str(bios.ReleaseDate)}
        report["cpu"] = c.Win32_Processor()[0].Name.strip()
        report["gpus"] = [g.Name.strip() for g in c.Win32_VideoController()]
        report["ram_gb"] = round(int(cs.TotalPhysicalMemory) / 1024**3, 1)
        report["os"] = c.Win32_OperatingSystem()[0].Caption
    except Exception:
        report["system_error"] = traceback.format_exc()

    for group, probes in PROBES.items():
        report["groups"][group] = [probe(ns, cls) for ns, cls in probes]

    report["awcc_methods"] = awcc_methods()
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"written: {OUT}")
    print(f"model: {report['model']}  bios: {report['bios']}")
    for g, rows in report["groups"].items():
        for r in rows:
            print(f"  {g:14} {r['class']:32} exists={r['exists']!s:5} instances={r['instances']} {r['error'] or ''}")


if __name__ == "__main__":
    main()