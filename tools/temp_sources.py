"""Which temperature source is real? Applies CPU load and watches every candidate.

Elevated. Writes docs/baseline/temp_sources.json
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "docs" / "baseline" / "temp_sources.json"


def acpi_zones() -> dict:
    out = {}
    try:
        import wmi
        for z in wmi.WMI(namespace="root\\WMI").MSAcpi_ThermalZoneTemperature():
            try:
                out[str(z.InstanceName)] = round(z.CurrentTemperature / 10.0 - 273.15, 1)
            except Exception:
                pass
    except Exception as ex:
        out['error'] = f'{type(ex).__name__}'
    return out


def perf_zones() -> dict:
    out = {}
    try:
        import wmi
        for z in wmi.WMI().Win32_PerfFormattedData_Counters_ThermalZoneInformation():
            try:
                out[str(z.Name)] = round(float(z.Temperature) / 10.0 - 273.15, 1)
            except Exception:
                pass
    except Exception as ex:
        out['error'] = f'{type(ex).__name__}'
    return out


def awcc_temps():
    try:
        from Backend.AWCCThermal import AWCCThermal
        a = AWCCThermal()
        temps = a.getAllTemp()
        rpm = a.getAllFanRPM()
        return {'sensor_temps': temps, 'fan_rpm': rpm}
    except Exception as ex:
        return {'error': f'{type(ex).__name__}: {ex}'}


def nvml_temp():
    try:
        import pynvml as n
        n.nvmlInit()
        h = n.nvmlDeviceGetHandleByIndex(0)
        t = n.nvmlDeviceGetTemperature(h, n.NVML_TEMPERATURE_GPU)
        n.nvmlShutdown()
        return t
    except Exception:
        return None


def snapshot():
    return {
        't': round(time.time(), 1),
        'acpi_zones': acpi_zones(),
        'perf_zones': perf_zones(),
        'awcc': awcc_temps(),
        'nvml_gpu': nvml_temp(),
    }


def main():
    data = {'idle': [snapshot()]}
    procs = [subprocess.Popen([sys.executable, str(ROOT / 'tools' / 'baseline_probe.py'), '--burn'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for _ in range(10)]
    try:
        for i in range(3):
            time.sleep(10)
            data[f'load_{i}'] = [snapshot()]
    finally:
        for p in procs:
            try: p.kill()
            except Exception: pass
    time.sleep(5)
    data['after'] = [snapshot()]
    OUT.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def show(tag, s):
        print(f"--- {tag} ---")
        print("  acpi zones:", s['acpi_zones'])
        print("  perf zones:", s['perf_zones'])
        print("  awcc     :", s['awcc'].get('sensor_temps'), "rpm", s['awcc'].get('fan_rpm'))
        print("  nvml gpu :", s['nvml_gpu'])

    for tag in ['idle', 'load_0', 'load_1', 'load_2', 'after']:
        if tag in data:
            show(tag, data[tag][0])
    print(f"written: {OUT}")


if __name__ == '__main__':
    main()
