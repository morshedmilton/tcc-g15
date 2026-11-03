import io

p = 'src/GUI/AppGUI.py'
lines = io.open(p, encoding='utf-8', newline='').read().split('\r\n')

# Find the line "# Update tray icon" and insert before it
for i, ln in enumerate(lines):
    if ln.strip() == '# Update tray icon':
        insert_at = i
        break

new_lines = [
    '            # Auto mode: fan speed follows CPU temperature curve',
    '            # 50 °C -> 3500 RPM, 80 °C+ -> max RPM (5500), linear between',
    '            if self._modeSwitch.getChecked() == ThermalMode.Auto.value and cpuTemp is not None:',
    '                if cpuTemp <= self._autoCurveMinTemp:',
    '                    targetRpm = self._autoCurveMinRpm',
    '                elif cpuTemp >= self._autoCurveMaxTemp:',
    '                    targetRpm = self._autoCurveMaxRpm',
    '                else:',
    '                    t = (cpuTemp - self._autoCurveMinTemp) / (self._autoCurveMaxTemp - self._autoCurveMinTemp)',
    '                    targetRpm = int(self._autoCurveMinRpm + t * (self._autoCurveMaxRpm - self._autoCurveMinRpm))',
    '                pct = int(round(targetRpm / self._autoCurveMaxRpm * 100))',
    '                pct = max(0, min(100, pct))',
    '                self._awcc.setFanSpeed(self._awcc.CPUFanIdx, pct)',
    '                self._awcc.setFanSpeed(self._awcc.GPUFanIdx, pct)',
    '                # Update sliders to show current auto speed',
    '                self._thermalCPU.setSpeedSlider(pct)',
    '                self._thermalGPU.setSpeedSlider(pct)',
    '',
]

lines[insert_at:insert_at] = new_lines
io.open(p, 'w', encoding='utf-8', newline='').write('\r\n'.join(lines))
print('done at', insert_at)