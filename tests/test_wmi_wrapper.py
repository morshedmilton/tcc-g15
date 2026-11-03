import pytest
from Backend.AWCCWmiWrapper import AWCCWmiWrapper

class FakeAwcc:
    def __init__(self, accepted_modes=()):
        self.calls = []
        self.accepted_modes = set(accepted_modes)

    def Thermal_Information(self, arg):
        self.calls.append(("TI", arg))
        return (0,)

    def GetFanSensors(self, arg):
        self.calls.append(("GF", arg))
        return (0,)

    def Thermal_Control(self, arg):
        self.calls.append(("TC", arg))
        mode = arg >> 8
        return (0,) if mode in self.accepted_modes else (-1,)


def last_mode(fake):
    tc_calls = [arg for method, arg in fake.calls if method == "TC"]
    assert len(tc_calls) > 0
    return tc_calls[-1] >> 8


def test_bit_packing():
    fake = FakeAwcc({0xA0, 0xAB})
    wrapper = AWCCWmiWrapper(fake)
    
    wrapper.GetSensorTemperature(1)
    wrapper.GetFanRPM(0x31)
    wrapper.SetAddonSpeedPercent(0x31, 100)

    expected = [
        ("TI", (1 << 8) | 4),
        ("TI", (0x31 << 8) | 5),
        ("TC", (100 << 16) | (0x31 << 8) | 2),
    ]
    assert fake.calls[:3] == expected


def test_ustt_firmware_modes_5530():
    fake = FakeAwcc({0xA0, 0xA1, 0xA3, 0xAB, 0x97})
    wrapper = AWCCWmiWrapper(fake)

    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Balanced)
    assert last_mode(fake) == 0xA0

    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Quiet)
    assert last_mode(fake) == 0xA3

    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Performance)
    assert last_mode(fake) == 0xA1

    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.G_Mode)
    assert last_mode(fake) == 0xAB


def test_legacy_firmware_fallback():
    fake = FakeAwcc({0x96, 0x97, 0x98, 0xAB})
    wrapper = AWCCWmiWrapper(fake)

    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Balanced)
    assert last_mode(fake) == 0x97

    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Quiet)
    assert last_mode(fake) == 0x96

    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Performance)
    assert last_mode(fake) == 0x98


def test_custom_mode_zero():
    fake = FakeAwcc({0})
    wrapper = AWCCWmiWrapper(fake)
    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Custom)
    assert last_mode(fake) == 0


def test_unsupported_mode_refusal():
    fake = FakeAwcc({0x97})
    wrapper = AWCCWmiWrapper(fake)
    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Quiet) is False


def test_mode_caching():
    fake = FakeAwcc({0xA3})
    wrapper = AWCCWmiWrapper(fake)

    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Quiet)
    calls_count = len([c for c in fake.calls if c[0] == "TC"])

    # Second call should use cache directly
    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Quiet)
    assert len([c for c in fake.calls if c[0] == "TC"]) == calls_count + 1


def test_invalid_wmi_returns_none():
    class NegativeWmi(FakeAwcc):
        def Thermal_Information(self, arg):
            return (-2,)

    class OverflowWmi(FakeAwcc):
        def Thermal_Information(self, arg):
            return (0xFFFFFFFF,)

    assert AWCCWmiWrapper(NegativeWmi()).GetFanRPMPercent(0x32) is None
    assert AWCCWmiWrapper(OverflowWmi()).GetSensorTemperature(1) is None


def test_thermal_mode_apply_retry():
    """Test that ApplyThermalMode retries once on transient WMI communication failure."""
    class FlakyAwcc(FakeAwcc):
        def __init__(self):
            super().__init__({0xA1})
            self.attempt = 0

        def Thermal_Control(self, arg):
            self.calls.append(("TC", arg))
            self.attempt += 1
            if self.attempt == 1:
                return (-1,)  # First attempt fails
            return (0,)  # Second attempt (retry) succeeds

    fake = FlakyAwcc()
    wrapper = AWCCWmiWrapper(fake)
    assert wrapper.ApplyThermalMode(wrapper.ThermalMode.Performance) is True
    assert fake.attempt == 2, "Expected 2 attempts (initial + 1 retry)"
