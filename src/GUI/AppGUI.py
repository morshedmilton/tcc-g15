import sys, os, time, datetime, subprocess, tempfile, ctypes
from ctypes import wintypes
from enum import Enum
from pathlib import Path
from typing import Callable, Literal, Optional, Tuple, List
from PySide6 import QtCore, QtGui, QtWidgets
from windows_toasts import WindowsToaster, Toast, ToastDuration, ToastDisplayImage
from Backend.AWCCThermal import AWCCThermal, NoAWCCWMIClass, CannotInstAWCCWMI
from GUI.QRadioButtonSet import QRadioButtonSet
from GUI.AppColors import Colors
from GUI.ThermalUnitWidget import ThermalUnitWidget
from GUI.QGaugeTrayIcon import QGaugeTrayIcon
from GUI import HotKey
from Backend.DetectHardware import DetectHardware, ALLOW_UNSUPPORTED_ENV, SUPPORTED_MODELS
from Backend.GpuTemp import GpuTemperature
# GUI.Diagnostics is imported lazily in createBugReport()

GUI_ICON = 'icons/gaugeIcon.png'
HEARTBEAT_FILE = os.path.join(tempfile.gettempdir(), 'tcc-g15.heartbeat')

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', wintypes.BYTE),
        ('BatteryFlag', wintypes.BYTE),
        ('BatteryLifePercent', wintypes.BYTE),
        ('SystemStatusFlag', wintypes.BYTE),
        ('BatteryLifeTime', wintypes.DWORD),
        ('BatteryFullLifeTime', wintypes.DWORD),
    ]

def getAcPowerStatus() -> Optional[bool]:
    """Returns True if on AC power, False if on battery, None if unknown."""
    try:
        status = SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            if status.ACLineStatus == 0:
                return False
            elif status.ACLineStatus == 1:
                return True
    except Exception:
        pass
    return None

def watchdogCommand(heartbeatPath: str) -> Optional[list]:
    """The watchdog ships next to the exe when frozen, or as a script when running from source."""
    if getattr(sys, 'frozen', False):
        exe = os.path.join(os.path.dirname(sys.executable), 'tcc-watchdog.exe')
        return [exe, heartbeatPath] if os.path.exists(exe) else None
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tcc-watchdog.py')
    return [sys.executable, script, heartbeatPath] if os.path.exists(script) else None

def resourcePath(relativePath: str = '.'):
    return os.path.join(sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.abspath('.'), relativePath)

def autorunTask(action: Literal['add', 'remove']) -> int:
    taskName = "TCC_G15"
    removeCmd = f'schtasks /delete /tn "{taskName}" /f'

    if action == 'add':
        exeFile = os.path.abspath(sys.argv[0])
        if not exeFile.lower().endswith('.exe'):
            return -100
        try:
            with open(resourcePath("tcc_g15_task.xml"), 'r', encoding='utf-8') as f:
                xml = f.read()
        except OSError:
            return -101
        xml = xml.replace('<!--EXE_FILE_PATH-->', exeFile)
        tmpXml = os.path.join(tempfile.gettempdir(), 'tcc_g15_task.xml')
        try:
            with open(tmpXml, 'w', encoding='utf-8') as f:
                f.write(xml)
        except OSError:
            return -102

        os.system(removeCmd)
        rc = os.system(f'schtasks /create /xml "{tmpXml}" /tn "{taskName}" /f')
        if rc != 0:
            return rc
        return 0 if os.system(f'schtasks /query /tn "{taskName}" >nul 2>&1') == 0 else -103
    else:
        return os.system(removeCmd)

def alert(title: str, message: str, type: QtWidgets.QMessageBox.Icon = QtWidgets.QMessageBox.Icon.Information, *, message2: Optional[str] = None) -> None:
    msg = QtWidgets.QMessageBox(type, title, message)
    msg.setWindowIcon(QtGui.QIcon(resourcePath(GUI_ICON)))
    if message2: msg.setInformativeText(message2)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.exec()

def confirm(title: str, message: str, options: Optional[Tuple[str, str]] = None, dontAskAgain: bool = False) -> Tuple[bool, Optional[bool]]:
    msg = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, title, message, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    msg.setWindowIcon(QtGui.QIcon(resourcePath(GUI_ICON)))

    if options is not None:
        msg.button(QtWidgets.QMessageBox.Yes).setText(options[0])
        msg.button(QtWidgets.QMessageBox.No).setText(options[1])

    cbDontAskAgain = None
    if dontAskAgain:
        cbDontAskAgain = QtWidgets.QCheckBox("Don't ask me again.", msg)
        msg.setCheckBox(cbDontAskAgain)

    return (msg.exec() == QtWidgets.QMessageBox.Yes, cbDontAskAgain is not None and cbDontAskAgain.isChecked() or None)

class QPeriodic:
    def __init__(self, parent: QtCore.QObject, periodMs: int, callback: Callable) -> None:
        self._tmr = QtCore.QTimer(parent)
        self._tmr.setInterval(periodMs)
        self._tmr.setSingleShot(False)
        self._tmr.timeout.connect(callback)
    def start(self):
        self._tmr.start()
    def stop(self):
        self._tmr.stop()
    def setInterval(self, ms: int) -> None:
        if self._tmr.interval() != ms:
            self._tmr.setInterval(ms)

class ThermalMode(Enum):
    Custom = 'Custom'
    Balanced = 'Balanced'
    Performance = 'Performance'
    Quiet = 'Quiet'
    G_Mode = 'G_Mode'

# Native display order
MODE_ORDER = [ThermalMode.Custom, ThermalMode.Balanced, ThermalMode.Performance, ThermalMode.Quiet, ThermalMode.G_Mode]

class SettingsKey(Enum):
    Mode = "app/mode"
    CPUFanSpeed = "app/fan/cpu/speed"
    CPUThresholdTemp = "app/fan/cpu/threshold_temp"
    GPUFanSpeed = "app/fan/gpu/speed"
    GPUThresholdTemp = "app/fan/gpu/threshold_temp"
    FailSafeIsOnFlag = "app/failsafe_is_on_flag"
    MinimizeOnCloseFlag = "app/minimize_on_close_flag"
    AutoBatterySwitch = "app/auto_battery_switch"

def errorExit(message: str, message2: Optional[str] = None) -> None:
    if not QtWidgets.QApplication.instance():
        QtWidgets.QApplication([])
    alert("Oh-oh", message, QtWidgets.QMessageBox.Icon.Critical, message2=message2)
    sys.exit(1)

class TCC_GUI(QtWidgets.QWidget):
    TEMP_UPD_PERIOD_MS = 2000
    TEMP_UPD_PERIOD_MS_HIDDEN = 5000
    FAILSAFE_CPU_TEMP = 95
    FAILSAFE_GPU_TEMP = 85
    FAILSAFE_HARD_CPU_TEMP = 100
    FAILSAFE_HARD_GPU_TEMP = 90
    FAILSAFE_TRIGGER_DELAY_SEC = 8
    FAILSAFE_HARD_TRIGGER_DELAY_SEC = 4
    FAILSAFE_RESET_AFTER_TEMP_IS_OK_FOR_SEC = 60
    FAILSAFE_UNKNOWN_GRACE_SEC = 60
    APP_NAME = "Thermal Control Center for Dell G15"
    APP_VERSION = "1.8.0"
    APP_DESCRIPTION = "This app is an open-source, highly efficient replacement for Alienware Command Center."
    APP_URL = "github.com/morshedmilton/tcc-g15"
    APP_CREDITS = "Original app & AWCC WMI research: github.com/AlexIII/tcc-g15\nMaintained fork for Dell G15 5530: github.com/morshedmilton/tcc-g15"

    # Color threshold limits (Green -> Yellow -> Red)
    GPU_COLOR_LIMITS = (72, 85)
    CPU_COLOR_LIMITS = (85, 95)

    _failsafeTempIsHighTs = 0
    _failsafeTempIsHighStartTs: Optional[float] = None
    _failsafeHardTempStartTs: Optional[float] = None
    _failsafeTrippedPrevModeStr: Optional[str] = None
    _cpuUnknownSince: Optional[float] = None
    _gpuUnknownSince: Optional[float] = None
    _failsafeOn = True
    _autoBatterySwitch = True
    _isAcPower: Optional[bool] = None
    _acPreferredMode: str = ThermalMode.Balanced.value
    _prevSavedSettingsValues: list = []

    _gModeKeySignal = QtCore.Signal()
    _gModeKeyPrevModeStr: Optional[str] = None

    _toaster = WindowsToaster(APP_NAME)
    _modeSwitch: QRadioButtonSet

    def __init__(self, awcc: AWCCThermal):
        super().__init__()
        self._awcc = awcc
        self._gpuTemp = GpuTemperature()
        print(f'GPU temperature source: {"NVML" if self._gpuTemp.available else "Dell WMI sensor"}')

        self.settings = QtCore.QSettings(self.APP_URL, "AWCC")
        print(f'Settings location: {self.settings.fileName()}')

        self.setWindowIcon(QtGui.QIcon(resourcePath(GUI_ICON)))
        self.mouseReleaseEvent = lambda evt: (
            evt.button() == QtCore.Qt.RightButton and
            alert("About", f"{self.APP_NAME} v{self.APP_VERSION}", message2=f"{self.APP_DESCRIPTION}\n\n{self.APP_CREDITS}")
        )

        # Set up tray icon
        self.trayIcon = QGaugeTrayIcon((self.GPU_COLOR_LIMITS, self.CPU_COLOR_LIMITS))
        menu = QtWidgets.QMenu()
        menu.addSection("Mode")
        self._trayMenuModeSwitch = {}
        for m in MODE_ORDER:
            modeAction = menu.addAction("-")
            modeAction.triggered.connect(lambda _, m_value=m.value: self._modeSwitch.setChecked(m_value))
            self._trayMenuModeSwitch[m.value] = modeAction

        menu.addSection("Automation")
        self._batterySwitchAction = menu.addAction("Auto-switch on battery")
        self._batterySwitchAction.setCheckable(True)
        self._batterySwitchAction.setChecked(self._autoBatterySwitch)
        self._batterySwitchAction.triggered.connect(self._toggleBatterySwitch)

        menu.addSection("Settings")
        showAction = menu.addAction("Show")
        showAction.triggered.connect(self.showNormal)
        addToAutorunAction = menu.addAction("Enable autorun")
        def autorunTaskRun(action: Literal['add', 'remove']) -> None:
            err = autorunTask(action)
            if err != 0 and action == 'add':
                alert("Error", f"Failed to {action} autorun task. Error={err}", QtWidgets.QMessageBox.Icon.Critical)
            else:
                alert("Success", f"Autorun on system startup {'Enabled' if action == 'add' else 'Disabled'}")
            if self.isMinimized():
                self.showMinimized()
                self.hide()
        addToAutorunAction.triggered.connect(lambda: autorunTaskRun('add'))
        removeFromAutorunAction = menu.addAction("Disable autorun")
        removeFromAutorunAction.triggered.connect(lambda: autorunTaskRun('remove'))
        restoreAction = menu.addAction("Restore Default")
        restoreAction.triggered.connect(self.clearAppSettings)
        bugReportAction = menu.addAction("Create bug report")
        bugReportAction.triggered.connect(self.createBugReport)
        exitAction = menu.addAction("Exit")
        exitAction.triggered.connect(self.onExit)

        tray = QtWidgets.QSystemTrayIcon(self)
        tray.setIcon(self.trayIcon)
        tray.setContextMenu(menu)
        tray.show()

        def onTrayIconActivated(trigger):
            if trigger == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
                self.showNormal()
                self.activateWindow()
        self.connect(tray, QtCore.SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), onTrayIconActivated)

        self.setObjectName('QMainWindow')
        self.setWindowTitle(self.APP_NAME)

        # Thermal Unit Widgets
        self._thermalGPU = ThermalUnitWidget(self, tempMinMax=(0, 95), tempColorLimits=self.GPU_COLOR_LIMITS, fanMinMax=(0, 5500), sliderMaxAndTick=(120, 20))
        self._thermalGPU.setTitle('GPU')
        self._thermalCPU = ThermalUnitWidget(self, tempMinMax=(0, 110), tempColorLimits=self.CPU_COLOR_LIMITS, fanMinMax=(0, 5500), sliderMaxAndTick=(120, 20))
        self._thermalCPU.setTitle('CPU')

        self._thermalGPU.setSourceNote(
            'GPU temperature: NVIDIA NVML (direct driver)' if self._gpuTemp.available
            else 'GPU temperature: Dell firmware sensor 6 (WMI)')
        self._thermalCPU.setSourceNote(
            'CPU temperature: Dell firmware sensor 1 (WMI board sensor). Verified on G15 5530.')

        # Detect GPU/CPU models asynchronously without freezing the UI
        class DetectCpuGpuModelsWorker(QtCore.QObject):
            finished = QtCore.Signal(str, str)
            def __init__(self, parent: QtCore.QObject, on_result: Callable[[Optional[str], Optional[str]], None]) -> None:
                super().__init__()
                self._t = QtCore.QThread(parent)
                self.moveToThread(self._t)
                self.finished.connect(self._t.quit)
                self.finished.connect(on_result)
                self._t.started.connect(self._task)
                self._t.start()
            def _task(self):
                d = DetectHardware()
                gpuModel = d.getHardwareName(d.GPUFanIdx)
                cpuModel = d.getHardwareName(d.CPUFanIdx)
                self.finished.emit(gpuModel, cpuModel)
            def start(self):
                self._t.start()
        detect = DetectCpuGpuModelsWorker(self, self.updateGaugeTitles)
        detect.start()

        lTherm = QtWidgets.QHBoxLayout()
        lTherm.setContentsMargins(0, 0, 0, 0)
        lTherm.setSpacing(10)
        lTherm.addWidget(self._thermalGPU)
        lTherm.addWidget(self._thermalCPU)

        # Mode Radio Button Set (clean 5 modes)
        self._modeSwitch = QRadioButtonSet(None, None, [(m.name.replace('_', ' '), m.value) for m in MODE_ORDER])

        # Fail-safe indicator
        failsafeIndicator = QtWidgets.QLabel()
        def updFailsafeIndicator() -> None:
            color = Colors.GREEN.value if self._failsafeOn else Colors.GREY.value
            msg = "Normal"
            if self._failsafeTempIsHighTs > 0:
                color = Colors.YELLOW.value
                timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._failsafeTempIsHighTs))
                msg = f"Last high temp at {timeStr}"
                if self._failsafeTrippedPrevModeStr is not None:
                    color = Colors.RED.value
                    msg = "Fail-safe ACTIVE: G-Mode forced"
            failsafeIndicator.setStyleSheet(f"QLabel {{ min-height: 14px; min-width: 14px; max-height: 14px; max-width: 14px; border: 1px solid {Colors.GREY.value}; border-radius: 7px; background: {color}; }}")
            failsafeIndicator.setToolTip(msg)
        self._updFailsafeIndicator = updFailsafeIndicator
        updFailsafeIndicator()

        # Fail-safe temp limit combos
        self._limitTempGPU = QtWidgets.QComboBox()
        self._limitTempGPU.addItems([str(v) for v in range(50, 91)])
        self._limitTempGPU.setToolTip("Threshold GPU temp (°C)")
        self._limitTempGPU.setMaximumWidth(55)

        self._limitTempCPU = QtWidgets.QComboBox()
        self._limitTempCPU.addItems([str(v) for v in range(50, 101)])
        self._limitTempCPU.setToolTip("Threshold CPU temp (°C)")
        self._limitTempCPU.setMaximumWidth(55)

        def onLimitGPUChange():
            val = self._limitTempGPU.currentText()
            if val.isdigit(): self.FAILSAFE_GPU_TEMP = int(val)
        self._limitTempGPU.currentIndexChanged.connect(onLimitGPUChange)

        def onLimitCPUChange():
            val = self._limitTempCPU.currentText()
            if val.isdigit(): self.FAILSAFE_CPU_TEMP = int(val)
        self._limitTempCPU.currentIndexChanged.connect(onLimitCPUChange)

        # Fail-safe checkbox
        self._failsafeCB = QtWidgets.QCheckBox("Fail-safe")
        self._failsafeCB.setToolTip(f"Switch to G-mode (100% cooling) when GPU reaches {self.FAILSAFE_GPU_TEMP}°C or CPU reaches {self.FAILSAFE_CPU_TEMP}°C.")
        def onFailsafeCB():
            self._failsafeOn = self._failsafeCB.isChecked()
            self._failsafeTempIsHighTs = 0
            self._failsafeTrippedPrevModeStr = None
            self._failsafeTempIsHighStartTs = None
            self._failsafeHardTempStartTs = None
            updFailsafeIndicator()
        self._failsafeCB.toggled.connect(onFailsafeCB)
        self._failsafeCB.setChecked(self._failsafeOn)

        # Fail-safe controls cluster
        failsafeBox = QtWidgets.QHBoxLayout()
        failsafeBox.setSpacing(6)
        failsafeBox.setContentsMargins(0, 0, 0, 0)
        failsafeBox.addWidget(self._failsafeCB)
        failsafeBox.addWidget(self._limitTempGPU)
        failsafeBox.addWidget(self._limitTempCPU)
        failsafeBox.addWidget(failsafeIndicator)

        # Single bottom control row: Mode switches on the left, fail-safe cluster on the right!
        ctrlBox = QtWidgets.QHBoxLayout()
        ctrlBox.setContentsMargins(4, 2, 4, 2)
        ctrlBox.setSpacing(10)
        ctrlBox.addWidget(self._modeSwitch, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        ctrlBox.addStretch(1)
        ctrlBox.addLayout(failsafeBox)

        # Main window layout: 2 rows only! Ultra compact and sleek!
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.setContentsMargins(8, 6, 8, 6)
        mainLayout.setSpacing(4)
        mainLayout.addLayout(lTherm)
        mainLayout.addLayout(ctrlBox)
        mainLayout.setAlignment(QtCore.Qt.AlignTop)

        # Set compact size constraints
        self.adjustSize()

        # Glue GUI to backend
        self.gModeHotKey = None
        self._updateGaugesTask = None

        def setFanSpeed(fan: Literal['GPU', 'CPU'], speed: int) -> None:
            res = self._awcc.setFanSpeed(self._awcc.GPUFanIdx if fan == 'GPU' else self._awcc.CPUFanIdx, speed)
            print(f'Set {fan} fan speed to {speed}: ' + ('ok' if res else 'fail'))

        def updateFanSpeed():
            if self._modeSwitch.getChecked() != ThermalMode.Custom.value:
                return
            setFanSpeed('GPU', self._thermalGPU.getSpeedSlider())
            setFanSpeed('CPU', self._thermalCPU.getSpeedSlider())

        self._thermalGPU.speedSliderChanged(updateFanSpeed)
        self._thermalCPU.speedSliderChanged(updateFanSpeed)

        self._lastGoodMode = ThermalMode.Balanced.value

        def onModeChange(val: str):
            isCustom = (val == ThermalMode.Custom.value)
            self._thermalGPU.setSpeedDisabled(not isCustom)
            self._thermalCPU.setSpeedDisabled(not isCustom)

            modeEnum = getattr(self._awcc.Mode, val, None)
            if modeEnum is None:
                print(f"Unknown mode {val}")
                return

            res = self._awcc.setMode(modeEnum)
            print(f'Set mode {val}: ' + ('ok' if res else 'fail'))
            if not res:
                if val in (ThermalMode.Quiet.value, ThermalMode.Performance.value):
                    print(f'Mode {val} is not supported here, hiding it')
                    self._modeSwitch.setOptionEnabled(val, False)
                    self._modeSwitch.setChecked(self._lastGoodMode)
                    self.toasterMessage(["Not supported", f"This firmware has no {val} profile", "Thermal mode"])
                    return
                self._errorExit(f"Failed to set mode {val}", "Program is terminated")

            self._lastGoodMode = val
            if isCustom:
                updateFanSpeed()
            if val != ThermalMode.G_Mode.value:
                self._failsafeTrippedPrevModeStr = None
            updFailsafeIndicator()
            for m in MODE_ORDER:
                if m.value in self._trayMenuModeSwitch:
                    self._trayMenuModeSwitch[m.value].setText(f"{'•' if m.value == val else ' '} {m.name.replace('_', ' ')}")

        self._modeSwitch.setOnChange(onModeChange)
        self._modeSwitch.setChecked(ThermalMode.Balanced.value)
        onModeChange(ThermalMode.Balanced.value)

        def updateAppState():
            self._touchHeartbeat()

            # NVML reads driver directly, eliminating the Dell WMI 2-3°C bug (#9)
            nvmlGpu = self._gpuTemp.read()
            gpuTemp = self._saneTemp(nvmlGpu if nvmlGpu is not None else self._awcc.getFanRelatedTemp(self._awcc.GPUFanIdx))
            gpuRPM = self._awcc.getFanRPM(self._awcc.GPUFanIdx)
            cpuTemp = self._saneTemp(self._awcc.getFanRelatedTemp(self._awcc.CPUFanIdx))
            cpuRPM = self._awcc.getFanRPM(self._awcc.CPUFanIdx)

            if gpuTemp is not None: self._thermalGPU.setTemp(gpuTemp)
            if gpuRPM is not None: self._thermalGPU.setFanRPM(gpuRPM)
            if cpuTemp is not None: self._thermalCPU.setTemp(cpuTemp)
            if cpuRPM is not None: self._thermalCPU.setFanRPM(cpuRPM)

            # Smart Power Automation: AC <-> Battery transitions
            if self._autoBatterySwitch:
                ac = getAcPowerStatus()
                if ac is not None and self._isAcPower is not None and ac != self._isAcPower:
                    currentMode = self._modeSwitch.getChecked()
                    if not ac:
                        # Switched to Battery: save AC mode, switch to Quiet to preserve battery & noise
                        if currentMode != ThermalMode.Quiet.value:
                            self._acPreferredMode = currentMode
                            self._modeSwitch.setChecked(ThermalMode.Quiet.value)
                            self.toasterMessage(["Battery Mode", "Switched to Quiet profile on battery", "Power Profile"])
                    else:
                        # Switched to AC: restore preferred AC mode
                        if currentMode == ThermalMode.Quiet.value and self._acPreferredMode:
                            self._modeSwitch.setChecked(self._acPreferredMode)
                            self.toasterMessage(["AC Connected", f"Restored {self._acPreferredMode} profile on AC", "Power Profile"])
                self._isAcPower = ac

            # Fail-Safe Handling
            now = time.time()
            self._cpuUnknownSince = None if cpuTemp is not None else (self._cpuUnknownSince or now)
            self._gpuUnknownSince = None if gpuTemp is not None else (self._gpuUnknownSince or now)
            def sensorGone(ts: Optional[float]) -> bool:
                return ts is not None and (now - ts) > self.FAILSAFE_UNKNOWN_GRACE_SEC

            # Normal user threshold check
            tempIsHigh = (
                (cpuTemp is not None and cpuTemp >= self.FAILSAFE_CPU_TEMP) or
                (gpuTemp is not None and gpuTemp >= self.FAILSAFE_GPU_TEMP) or
                sensorGone(self._cpuUnknownSince) or sensorGone(self._gpuUnknownSince)
            )

            # Hard safety limit (cannot be bypassed, Principle 2a)
            hardTempIsHigh = (
                (cpuTemp is not None and cpuTemp >= self.FAILSAFE_HARD_CPU_TEMP) or
                (gpuTemp is not None and gpuTemp >= self.FAILSAFE_HARD_GPU_TEMP)
            )

            if tempIsHigh or hardTempIsHigh:
                self._failsafeTempIsHighTs = time.time()

            self._failsafeTempIsHighStartTs = (self._failsafeTempIsHighStartTs or time.time()) if tempIsHigh else None
            self._failsafeHardTempStartTs = (self._failsafeHardTempStartTs or time.time()) if hardTempIsHigh else None

            # Trip conditions:
            # 1. User failsafe enabled + continuous high temp for debounce period
            # 2. Hard failsafe emergency (even if unchecked) + hard threshold sustained
            userTrip = (
                self._failsafeOn and
                self._modeSwitch.getChecked() != ThermalMode.G_Mode.value and
                tempIsHigh and
                self._failsafeTempIsHighStartTs is not None and
                (time.time() - self._failsafeTempIsHighStartTs) > self.FAILSAFE_TRIGGER_DELAY_SEC
            )
            hardTrip = (
                self._modeSwitch.getChecked() != ThermalMode.G_Mode.value and
                hardTempIsHigh and
                self._failsafeHardTempStartTs is not None and
                (time.time() - self._failsafeHardTempStartTs) > self.FAILSAFE_HARD_TRIGGER_DELAY_SEC
            )

            if userTrip or hardTrip:
                self._failsafeTrippedPrevModeStr = self._modeSwitch.getChecked()
                self._modeSwitch.setChecked(ThermalMode.G_Mode.value)
                self._toasterMessageCurrentMode(source='failsafe')
                print(f'Fail-safe tripped (hard={hardTrip}) at GPU={gpuTemp} CPU={cpuTemp}')

            # Auto-reset failsafe
            if (self._failsafeTrippedPrevModeStr is not None and
                (time.time() - self._failsafeTempIsHighTs) > self.FAILSAFE_RESET_AFTER_TEMP_IS_OK_FOR_SEC
            ):
                self._modeSwitch.setChecked(self._failsafeTrippedPrevModeStr)
                self._toasterMessageCurrentMode(source='failsafe')
                self._failsafeTrippedPrevModeStr = None
                print('Fail-safe reset')

            # Update tray icon
            self.trayIcon = self.trayIcon.resizeForScreen() or self.trayIcon
            self.trayIcon.update((gpuTemp, cpuTemp), self._modeSwitch.getChecked() == ThermalMode.G_Mode.value)
            tray.setIcon(self.trayIcon)
            tray.setToolTip(f"GPU: {gpuTemp or '--'} °C    {gpuRPM or '--'} RPM\nCPU: {cpuTemp or '--'} °C    {cpuRPM or '--'} RPM\nMode: {self._modeSwitch.getChecked().replace('_', ' ')}")

            # Poll slower when minimized to tray (saves power & wakeups)
            self._updateGaugesTask.setInterval(
                self.TEMP_UPD_PERIOD_MS if self.isVisible() else self.TEMP_UPD_PERIOD_MS_HIDDEN)

            self._saveAppSettings()

        self._loadAppSettings()

        self._updateGaugesTask = QPeriodic(self, self.TEMP_UPD_PERIOD_MS, updateAppState)
        updateAppState()
        self._updateGaugesTask.start()

        self._watchdog = None
        self._watchdogPid = None
        self._startWatchdog()

        self.gModeHotKey = HotKey.HotKey(HotKey.G_MODE_KEY, self._gModeKeySignal)
        self._gModeKeySignal.connect(self._onGModeHotKeyPressed)
        self.gModeHotKey.start()

    def _toggleBatterySwitch(self, checked: bool) -> None:
        self._autoBatterySwitch = checked

    def updateGaugeTitles(self, gpuModel, cpuModel):
        if gpuModel: self._thermalGPU.setTitle(gpuModel)
        if cpuModel: self._thermalCPU.setTitle(cpuModel)

    def closeEvent(self, event):
        minimizeOnClose = self.settings.value(SettingsKey.MinimizeOnCloseFlag.value)
        if minimizeOnClose is not None:
            minimizeOnClose = str(minimizeOnClose).lower() == 'true'

        if minimizeOnClose is None:
            (toExit, dontAskAgain) = confirm("Exit", "Do you want to exit or minimize to tray?", ("Exit", "Minimize"), True)
            minimizeOnClose = not toExit
            if dontAskAgain:
                self.settings.setValue(SettingsKey.MinimizeOnCloseFlag.value, minimizeOnClose)

        if minimizeOnClose:
            event.ignore()
            self.hide()
        else:
            self.onExit()

    def onExit(self):
        print("exit")
        prevMode = self._modeSwitch.getChecked()
        self._modeSwitch.setChecked(ThermalMode.Balanced.value)
        if prevMode != ThermalMode.Balanced.value:
            self._toasterMessageCurrentMode()
        self._destroy()
        sys.exit(0)

    def _errorExit(self, message: str, message2: Optional[str] = None) -> None:
        self._destroy()
        errorExit(message, message2)

    def _destroy(self):
        if self.gModeHotKey is not None:
            self.gModeHotKey.stop()
            self.gModeHotKey.wait()
        if self._updateGaugesTask is not None:
            self._updateGaugesTask.stop()
        self._stopWatchdog()
        if getattr(self, '_gpuTemp', None) is not None:
            self._gpuTemp.shutdown()

    def _startWatchdog(self) -> None:
        cmd = watchdogCommand(HEARTBEAT_FILE)
        if not cmd:
            print('Watchdog: not available (not bundled), skipping')
            return
        try:
            Path(HEARTBEAT_FILE).write_text('', encoding='utf-8')
        except OSError:
            pass

        # Launch detached through WMI so it survives taskkill /T
        try:
            import wmi
            creation = wmi.WMI().Win32_Process.Create(
                CommandLine=' '.join(f'"{part}"' for part in cmd))
            pid = int(creation[1])
            if pid:
                self._watchdogPid = pid
                print(f'Watchdog: started pid {pid} (detached via WMI)')
                return
        except Exception as ex:
            print(f'Watchdog: WMI launch failed ({type(ex).__name__}), falling back to Popen')

        try:
            self._watchdog = subprocess.Popen(cmd, close_fds=True)
            print(f'Watchdog: started pid {self._watchdog.pid} (child)')
        except Exception as ex:
            print(f'Watchdog: failed to start ({type(ex).__name__}: {ex})')

    def _stopWatchdog(self) -> None:
        if getattr(self, '_watchdogPid', None):
            try:
                import wmi
                for proc in wmi.WMI().Win32_Process(ProcessId=self._watchdogPid):
                    proc.Terminate()
                print(f'Watchdog: stopped pid {self._watchdogPid}')
            except Exception as ex:
                print(f'Watchdog: stop failed ({type(ex).__name__})')
            self._watchdogPid = None
        if getattr(self, '_watchdog', None) is not None:
            self._watchdog.terminate()
            self._watchdog = None

    def _touchHeartbeat(self) -> None:
        try:
            Path(HEARTBEAT_FILE).touch()
        except OSError:
            pass

    def createBugReport(self) -> None:
        try:
            from GUI import Diagnostics
            zipPath, url = Diagnostics.build(self.APP_NAME, self.APP_VERSION)
        except Exception as ex:
            alert("Diagnostics failed", f"{type(ex).__name__}: {ex}", QtWidgets.QMessageBox.Icon.Critical)
            return
        import webbrowser
        if zipPath:
            webbrowser.open(f'file:///{zipPath}')
        webbrowser.open(url)
        alert("Bug report ready",
              "A redacted diagnostics zip was created and the issue page is open.",
              message2=f"{zipPath}\n\nAttach the zip to the issue.")
        print('Cleanup: done')

    def _onGModeHotKeyPressed(self):
        current = self._modeSwitch.getChecked()
        if current == ThermalMode.G_Mode.value:
            self._modeSwitch.setChecked(self._gModeKeyPrevModeStr or ThermalMode.Balanced.value)
        else:
            self._gModeKeyPrevModeStr = current
            self._modeSwitch.setChecked(ThermalMode.G_Mode.value)
        self._toasterMessageCurrentMode()

    def _toasterMessageCurrentMode(self, source: Optional[Literal['failsafe']] = None) -> None:
        sourceStr = " [Fail-safe]" if source == 'failsafe' else ""
        self.toasterMessage(
            [
                self._modeSwitch.getChecked().replace('_', ' '),
                f"GPU: {self._thermalGPU.getTemp()}°C, CPU: {self._thermalCPU.getTemp()}°C",
                "Thermal mode changed" + sourceStr
            ],
            source != 'failsafe'
        )

    def toasterMessage(self, message: List[str | None], expire=True) -> None:
        toast = Toast(duration=ToastDuration.Short, expiration_time=(datetime.datetime.now() + datetime.timedelta(seconds=5)) if expire else None)
        toast.text_fields = message
        toast.AddImage(ToastDisplayImage.fromPath(resourcePath(GUI_ICON)))
        self._toaster.show_toast(toast)

    @staticmethod
    def _saneTemp(t: Optional[int]) -> Optional[int]:
        return t if isinstance(t, int) and 5 <= t <= 120 else None

    def _saveAppSettings(self):
        modeToSave = self._modeSwitch.getChecked()
        if modeToSave == ThermalMode.G_Mode.value:
            modeToSave = self._gModeKeyPrevModeStr or ThermalMode.Balanced.value
        curValues = [
            modeToSave,
            self._thermalCPU.getSpeedSlider(),
            self._thermalGPU.getSpeedSlider(),
            self.FAILSAFE_CPU_TEMP,
            self.FAILSAFE_GPU_TEMP,
            self._failsafeOn,
            self._autoBatterySwitch
        ]
        if curValues == self._prevSavedSettingsValues:
            return
        self._prevSavedSettingsValues = curValues

        self.settings.setValue(SettingsKey.Mode.value, modeToSave)
        self.settings.setValue(SettingsKey.CPUFanSpeed.value, self._thermalCPU.getSpeedSlider())
        self.settings.setValue(SettingsKey.GPUFanSpeed.value, self._thermalGPU.getSpeedSlider())
        self.settings.setValue(SettingsKey.CPUThresholdTemp.value, self.FAILSAFE_CPU_TEMP)
        self.settings.setValue(SettingsKey.GPUThresholdTemp.value, self.FAILSAFE_GPU_TEMP)
        self.settings.setValue(SettingsKey.FailSafeIsOnFlag.value, self._failsafeOn)
        self.settings.setValue(SettingsKey.AutoBatterySwitch.value, self._autoBatterySwitch)

    def _loadAppSettings(self):
        savedMode = self.settings.value(SettingsKey.Mode.value)
        if savedMode not in [m.value for m in MODE_ORDER] or savedMode == ThermalMode.G_Mode.value:
            savedMode = ThermalMode.Balanced.value
        self._modeSwitch.setChecked(savedMode)
        savedSpeed = self.settings.value(SettingsKey.CPUFanSpeed.value)
        self._thermalCPU.setSpeedSlider(savedSpeed)
        savedSpeed = self.settings.value(SettingsKey.GPUFanSpeed.value)
        self._thermalGPU.setSpeedSlider(savedSpeed)
        savedTemp = self.settings.value(SettingsKey.CPUThresholdTemp.value) or 95
        self._limitTempCPU.setCurrentText(str(savedTemp))
        savedTemp = self.settings.value(SettingsKey.GPUThresholdTemp.value) or 85
        self._limitTempGPU.setCurrentText(str(savedTemp))
        savedFailsafe = self.settings.value(SettingsKey.FailSafeIsOnFlag.value) or 'true'
        self._failsafeCB.setChecked(str(savedFailsafe).lower() == 'true')
        savedBattery = self.settings.value(SettingsKey.AutoBatterySwitch.value)
        if savedBattery is not None:
            self._autoBatterySwitch = str(savedBattery).lower() == 'true'
            self._batterySwitchAction.setChecked(self._autoBatterySwitch)

    def clearAppSettings(self):
        (isYes, _) = confirm("Reset to Default", "Do you want to reset all settings to default?", ("Reset", "Cancel"))
        if not isYes: return
        self.settings.clear()
        self._loadAppSettings()

    def G_Mode_key_Pressed(self, val):
        print("G_Mode_key " + str(val))

def runApp(startMinimized=False) -> int:
    app = QtWidgets.QApplication([])

    try:
        awcc = AWCCThermal()
    except NoAWCCWMIClass:
        errorExit("AWCC WMI class not found in the system.", "You don't have some drivers installed or your system is not supported.")
    except CannotInstAWCCWMI:
        errorExit("Couldn't instantiate AWCC WMI class.", "Make sure you're running as Admin.")

    try:
        model = DetectHardware().getModelName()
    except Exception:
        model = None
    if not DetectHardware.isSupportedModel(model) and not DetectHardware.isUnsupportedAllowed():
        errorExit(
            "This laptop model is not verified.",
            f"Detected: {model}\n\nThis fork was only tested on: {', '.join(SUPPORTED_MODELS)}.\n"
            f"If you want to try anyway, set the environment variable {ALLOW_UNSUPPORTED_ENV}=1."
        )

    mainWindow = TCC_GUI(awcc)
    mainWindow.setStyleSheet(f"""
        QGauge {{
            border: 1px solid gray;
            border-radius: 3px;
            background-color: {Colors.GREY.value};
        }}
        QGauge::chunk {{
            background-color: {Colors.BLUE.value};
        }}
        * {{
            color: {Colors.WHITE.value};
            background-color: {Colors.DARK_GREY.value};
        }}
        QToolTip {{
            background-color: black; 
            color: {Colors.WHITE.value};
            border: 1px solid {Colors.DARK_GREY.value};
            border-radius: 3px;
        }}
        QComboBox {{
            border: 1px solid gray;
            border-radius: 3px;
            padding: 1px 0.6em 1px 3px;
        }}
        QComboBox::disabled {{
            color: {Colors.GREY.value};
        }}
        QRadioButton {{
            spacing: 5px;
            padding: 1px 2px;
        }}
        QRadioButton::indicator {{
            width: 12px;
            height: 12px;
            border-radius: 6px;
            border: 1px solid {Colors.GREY.value};
            background: {Colors.DARK_GREY.value};
        }}
        QRadioButton::indicator:checked {{
            border: 3px solid {Colors.BLUE.value};
            background: {Colors.WHITE.value};
        }}
        QRadioButton::indicator:disabled {{
            border-color: {Colors.DARK_GREY.value};
        }}
        QRadioButton:checked {{
            font-weight: bold;
            color: {Colors.WHITE.value};
        }}
        QRadioButton:disabled {{
            color: {Colors.GREY.value};
        }}
    """)

    # Compact window fitting
    mainWindow.adjustSize()
    mainWindow.setFixedSize(mainWindow.sizeHint())

    if startMinimized:
        mainWindow.showMinimized()
        mainWindow.hide()
    else:
        mainWindow.show()

    return app.exec()
