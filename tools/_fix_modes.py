import io

p = 'src/GUI/AppGUI.py'
lines = io.open(p, encoding='utf-8', newline='').read().split('\r\n')

# Fix updateFanSpeed to also allow Auto mode (so sliders work when manually overridden)
# Lines 351-355:
#         def updateFanSpeed():
#             if self._modeSwitch.getChecked() != ThermalMode.Custom.value:
#                 return
#             setFanSpeed('GPU', self._thermalGPU.getSpeedSlider())
#             setFanSpeed('CPU', self._thermalCPU.getSpeedSlider())

# Change to also allow manual override in Auto mode (but Auto normally controls it)
for i, ln in enumerate(lines):
    if ln.strip() == 'def updateFanSpeed():':
        # Check next few lines
        if 'ThermalMode.Custom.value' in lines[i+1]:
            lines[i+1] = '            if self._modeSwitch.getChecked() not in (ThermalMode.Custom.value, ThermalMode.Auto.value):'
            print('updated updateFanSpeed at', i+1)
            break

# Fix onModeChange to handle Auto mode - disable sliders in Auto mode too
# Line 362-363:
#             self._thermalGPU.setSpeedDisabled(val != ThermalMode.Custom.value)
#             self._thermalCPU.setSpeedDisabled(val != ThermalMode.Custom.value)

for i, ln in enumerate(lines):
    if ln.strip() == 'def onModeChange(val: str):':
        # Check the next lines for setSpeedDisabled
        for j in range(i+1, i+10):
            if 'setSpeedDisabled' in lines[j] and 'ThermalMode.Custom.value' in lines[j]:
                lines[j] = lines[j].replace('ThermalMode.Custom.value', '(ThermalMode.Custom.value, ThermalMode.Auto.value)')
                print('updated setSpeedDisabled at', j+1)
                break
        break

io.open('src/GUI/AppGUI.py', 'w', encoding='utf-8', newline='').write('\r\n'.join(lines))
print('done')