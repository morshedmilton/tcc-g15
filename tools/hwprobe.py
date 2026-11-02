"""Read-only AWCC WMI probe for Dell G15 5530. Requires admin. Changes nothing."""
import sys, os, json, traceback

ROOT = r"C:\Users\morsh\AppData\Roaming\AutoClaw-oversea-official\accounts\98e17ebcdf311a8f97d63ba37e0764ae6703014cbe59f58a71e626853184e80c\projects\Default"
sys.path.insert(0, os.path.join(ROOT, "tcc-g15", "src"))
OUT = os.path.join(ROOT, "tcc-g15-research", "hwprobe-5530.json")

def main():
    from wmi import WMI
    from Backend.AWCCWmiWrapper import AWCCWmiWrapper
    data = {"model": None, "class_found": False, "fans": [], "sensors": {}, "error": None}
    try:
        cs = WMI().Win32_ComputerSystem()[0]
        data["model"] = f"{cs.Manufacturer} {cs.Model}".strip()
        cls = WMI(namespace="root\\WMI").AWCCWmiMethodFunction
        data["class_found"] = True
        inst = cls()[0]
        w = AWCCWmiWrapper(inst)
        for fan_id, sensor_ids in w.GetFanIdsAndRelatedSensorsIds():
            data["fans"].append({
                "fan_id": fan_id,
                "sensor_ids": list(sensor_ids),
                "rpm": w.GetFanRPM(fan_id),
                "rpmpct": w.GetFanRPMPercent(fan_id),
                "sensors": [{"id": s, "temp": w.GetSensorTemperature(s)} for s in sensor_ids],
            })
        # scan every documented sensor id so we know which ones are live on this board
        for sid in range(AWCCWmiWrapper.SENSOR_ID_FIRST, AWCCWmiWrapper.SENSOR_ID_LAST + 1):
            t = w.GetSensorTemperature(sid)
            if t is not None:
                data["sensors"][str(sid)] = t
    except Exception:
        data["error"] = traceback.format_exc()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("written:", OUT)

if __name__ == "__main__":
    main()
