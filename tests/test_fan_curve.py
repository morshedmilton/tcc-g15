"""Tests for the Auto fan curve and the 4-profile rule targets (Cycle 007, REQ-701/702)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from Backend.FanCurve import (  # noqa: E402
    DEFAULT_CURVE,
    CurvePoint,
    FanCurveDriver,
    interpolate,
)
from Backend.ProcessRule import ProcessRule  # noqa: E402


# ---------------------------------------------------------------- curve maths
def test_anchor_points_are_exact():
    assert interpolate(50.0) == 64      # owner anchor: 50 C -> ~3500 rpm
    assert interpolate(80.0) == 100     # owner anchor: 80 C -> full speed


def test_midpoint_is_linear():
    # halfway between 50 C (64 %) and 80 C (100 %) is 82 %
    assert interpolate(65.0) == 82


def test_below_and_above_are_clamped():
    assert interpolate(10.0) == 64      # never below the first anchor
    assert interpolate(120.0) == 100    # never above 100 %
    assert interpolate(-40.0) == 64


def test_curve_is_monotonic():
    values = [interpolate(t) for t in range(30, 101)]
    assert values == sorted(values), "hotter must never mean less cooling"


def test_percent_is_always_in_range():
    for t in range(-20, 140):
        assert 0 <= interpolate(float(t)) <= 100


def test_custom_points_are_respected():
    pts = (CurvePoint(40, 30), CurvePoint(60, 50), CurvePoint(90, 100))
    assert interpolate(50, pts) == 40
    assert interpolate(75, pts) == 75
    assert interpolate(95, pts) == 100


# ---------------------------------------------------------------- write policy
def test_first_reading_always_writes():
    d = FanCurveDriver()
    assert d.plan("cpu", 60.0, now=0.0) == 76   # 50 C=64 %, 80 C=100 %, linear between


def test_none_temperature_never_writes():
    d = FanCurveDriver()
    assert d.plan("cpu", None, now=0.0) is None
    d.confirm("cpu", 80, 0.0)
    # a sensor dropout must not lower cooling: keep the last target, write nothing
    assert d.plan("cpu", None, now=100.0) is None
    assert d.last_applied("cpu") == 80


def test_deadband_suppresses_small_changes():
    d = FanCurveDriver(deadband_pct=3, min_interval_s=0)
    d.confirm("cpu", 64, 0.0)
    assert d.plan("cpu", 50.5, now=10.0) is None   # 65 % vs 64 % -> 1 point away
    assert d.plan("cpu", 65.0, now=10.0) == 82     # 82 % -> 18 points away


def test_rate_limit_blocks_then_allows():
    d = FanCurveDriver(deadband_pct=0, min_interval_s=1.5)
    d.confirm("cpu", 70, 0.0)
    assert d.plan("cpu", 80.0, now=0.5) is None
    assert d.plan("cpu", 80.0, now=2.0) == 100


def test_fans_are_independent():
    d = FanCurveDriver(deadband_pct=0, min_interval_s=1.5)
    d.confirm("cpu", 70, 0.0)
    # the GPU fan has never been written, so it is not rate-limited by the CPU fan
    assert d.plan("gpu", 80.0, now=0.1) == 100


def test_confirm_updates_state():
    d = FanCurveDriver(deadband_pct=0, min_interval_s=0)
    assert d.plan("cpu", 80.0, now=1.0) == 100
    d.confirm("cpu", 100, 1.0)
    assert d.last_applied("cpu") == 100
    assert d.plan("cpu", 80.0, now=2.0) is None


def test_reset_clears_state():
    d = FanCurveDriver()
    d.confirm("cpu", 90, 0.0)
    d.reset()
    assert d.last_applied("cpu") is None


# ---------------------------------------------------------------- rule targets
def test_legacy_performance_target_becomes_auto():
    rule = ProcessRule(process_name="cs2.exe", target_mode="Performance").with_visible_target()
    assert rule.target_mode == "Auto"


def test_legacy_quiet_target_becomes_balanced():
    rule = ProcessRule(process_name="notepad.exe", target_mode="Quiet").with_visible_target()
    assert rule.target_mode == "Balanced"


def test_visible_profiles_are_accepted_unchanged():
    for mode in ("Auto", "Balanced", "G_Mode", "Custom"):
        assert ProcessRule(process_name="x.exe", target_mode=mode).target_mode == mode


def test_space_form_is_normalised():
    assert ProcessRule(process_name="x.exe", target_mode="G Mode").target_mode == "G_Mode"


def test_default_presets_only_use_visible_profiles():
    from Backend.ProcessRulePresets import get_default_presets

    for rule in get_default_presets():
        assert rule.target_mode in ("Auto", "Balanced", "G_Mode", "Custom"), rule

# ---------------------------------------------------------------- arbitration & parsing
def test_auto_outranks_balanced_in_arbitration():
    """DEF-704: Auto had no rank, so a Balanced rule could win against it."""
    from Backend.ProcessRule import COOLING_SEVERITY_ORDER

    assert COOLING_SEVERITY_ORDER["Auto"] > COOLING_SEVERITY_ORDER["Balanced"]
    assert ProcessRule("game.exe", "Auto") > ProcessRule("app.exe", "Balanced")


def test_g_mode_still_outranks_everything():
    from Backend.ProcessRule import COOLING_SEVERITY_ORDER

    ranked = [ProcessRule("x.exe", m) for m in COOLING_SEVERITY_ORDER]
    assert max(ranked).target_mode == "G_Mode"


def test_enabled_false_string_is_honoured():
    """DEF-708: bool("false") is True, which silently re-enabled a disabled rule."""
    for raw in ("false", "0", "no", "off", False):
        assert ProcessRule.from_dict({"process_name": "a.exe", "enabled": raw}).enabled is False
    for raw in ("true", "1", "yes", True):
        assert ProcessRule.from_dict({"process_name": "a.exe", "enabled": raw}).enabled is True


def test_with_visible_target_is_idempotent_for_visible_modes():
    for mode in ("Auto", "Balanced", "G_Mode", "Custom"):
        rule = ProcessRule("x.exe", mode)
        assert rule.with_visible_target().target_mode == mode


def test_dialog_offers_exactly_the_window_profiles():
    """DEF-711: the dialog listed profiles the window no longer shows."""
    from GUI.AppGUI import MODE_ORDER
    from GUI.ProcessRulesDialog import SUPPORTED_MODES

    assert SUPPORTED_MODES == [m.value for m in MODE_ORDER]
