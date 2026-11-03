import sys, os, time, datetime, subprocess, tempfile
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
# GUI.Diagnostics is imported lazily in createBugReport(): it pulls zipfile/urllib and is only
# needed when someone actually files a bug.

GUI_ICON = 'icons/gaugeIcon.png'
HEARTBEAT_FILE = os.path.join(tempfile.gettempdir(), 'tcc-g15.heartbeat')

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
        # Patch a copy in temp: the bundled XML can be read-only (and must not be mutated).
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
        # Verify instead of trusting the exit code: upstream's task silently didn't exist.
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
    msg = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, title, message, QtWidgets.QMessageBox.Yes |  QtWidgets.QMessageBox.No)
    msg.setWindowIcon(QtGui.QIcon(resourcePath(GUI_ICON)))

    if options is not None:
        msg.button(QtWidgets.QMessageBox.Yes).setText(options[0])
        msg.button(QtWidgets.QMessageBox.No).setText(options[1])

    cbDontAskAgain = None
    if dontAskAgain:
        cbDontAskAgain = QtWidgets.QCheckBox('Don\'t ask me again.', msg)
        msg.setCheckBox(cbDontAskAgain)

    return (msg.exec_() == QtWidgets.QMessageBox.Yes, cbDontAskAgain is not None and cbDontAskAgain.isChecked() or None)


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
    Auto = 'Auto'
    Balanced = 'Balanced'
    G_Mode = 'G_Mode'
    Custom = 'Custom'

# display order: Auto first, then the explicit modes
MODE_ORDER = [ThermalMode.Auto, ThermalMode.Balanced, ThermalMode.G_Mode, ThermalMode.Custom]
    
class SettingsKey(Enum):
    Mode = "app/mode"
    CPUFanSpeed = "app/fan/cpu/speed"
    CPUThresholdTemp = "app/fan/cpu/threshold_temp"
    GPUFanSpeed = "app/fan/gpu/speed"
    GPUThresholdTemp = "app/fan/gpu/threshold_temp"
    FailSafeIsOnFlag = "app/failsafe_is_on_flag"
    MinimizeOnCloseFlag = "app/minimize_on_close_flag"

def errorExit(message: str, message2: Optional[str] = None) -> None:
    if not QtWidgets.QApplication.instance():
         QtWidgets.QApplication([])
    alert("Oh-oh", message, QtWidgets.QMessageBox.Icon.Critical, message2 = message2)
    sys.exit(1)

class TCC_GUI(QtWidgets.QWidget):
    TEMP_UPD_PERIOD_MS = 2000
    TEMP_UPD_PERIOD_MS_HIDDEN = 5000
    FAILSAFE_CPU_TEMP = 95
    FAILSAFE_GPU_TEMP = 85
    FAILSAFE_TRIGGER_DELAY_SEC = 8
    FAILSAFE_RESET_AFTER_TEMP_IS_OK_FOR_SEC = 60
    FAILSAFE_UNKNOWN_GRACE_SEC = 60
    APP_NAME = "Thermal Control Center for Dell G15"
    APP_VERSION = "1.8.0-beta1"
    APP_DESCRIPTION = "This app is an open-source replacement for Alienware Control Center "
    APP_URL = "github.com/morshedmilton/tcc-g15"
    APP_CREDITS = "Original app and AWCC WMI research: github.com/AlexIII/tcc-g15\nMaintained fork for Dell G15 5530: github.com/morshedmilton/tcc-g15"

    # Green to Yellow and Yellow to Red thresholds
    GPU_COLOR_LIMITS = (72, 85)
    CPU_COLOR_LIMITS = (85, 95)

    # private
    _failsafeTempIsHighTs = 0                           # Last time when the temp was registered to be high
    _failsafeTempIsHighStartTs: Optional[int] = None    # Time when the temp first registered to be high (without going lower than the threshold)
    _failsafeTrippedPrevModeStr: Optional[str] = None   # Mode (Custom, Balanced) before fail-safe tripped, as a string
    _cpuUnknownSince: Optional[float] = None            # When the CPU sensor first stopped answering
    _gpuUnknownSince: Optional[float] = None            # When the GPU sensor first stopped answering
    _failsafeOn = True
    _prevSavedSettingsValues: list = []

    _gModeKeySignal = QtCore.Signal()
    _gModeKeyPrevModeStr: Optional[str] = None

    _toaster = WindowsToaster(APP_NAME)

    _modeSwitch: QRadioButtonSet

    def __init__(self, awcc: AWCCThermal):
        super().__init__()
        self._awcc = awcc
        self._gpuTemp = GpuTemperature()   # before the first updateAppState() call
        print(f'GPU temperature source: {"NVML" if self._gpuTemp.available else "Dell WMI sensor"}')

        self.settings = QtCore.QSettings(self.APP_URL, "AWCC")
        print(f'Settings location: {self.settings.fileName()}')

        # Set main window props
        # Set main window props
        # Fixed size to hold two thermal panels (380*2 + margins) + 5 mode buttons + failsafe row.
        # adjustSize() fails because the layout's sizeHint is too optimistic (it can squeeze).
        self.setFixedSize(888, 299)
        self.setWindowIcon(QtGui.QIcon(resourcePath(GUI_ICON)))
        self.mouseReleaseEvent = lambda evt: (
            evt.button() == QtCore.Qt.RightButton and
            alert("About", f"{self.APP_NAME} v{self.APP_VERSION}", message2 = f"{self.APP_DESCRIPTION}\n\n{self.APP_CREDITS}")
        )

        # Set up tray icon
        self.trayIcon = QGaugeTrayIcon((self.GPU_COLOR_LIMITS, self.CPU_COLOR_LIMITS))
        menu = QtWidgets.QMenu()
        # Mode switch
        menu.addSection("Mode")
        self._trayMenuModeSwitch = {} # Dict[ThermalMode, QtWidgets.QAction]
        for m in ThermalMode:
            modeAction = menu.addAction("-")
            modeAction.triggered.connect(lambda _, m_value=m.value: self._modeSwitch.setChecked(m_value))
            self._trayMenuModeSwitch[m.value] = modeAction
        # Settings
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
            # When in minimized state, a wired bug causes the app to close if we won't touch some of the `self.show*()` methods
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
        # Setup tray widget
        tray = QtWidgets.QSystemTrayIcon(self)
        tray.setIcon(self.trayIcon)
        tray.setContextMenu(menu)
        tray.show()

        def onTrayIconActivated(trigger):
            if trigger == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
                self.showNormal()
                self.activateWindow()
        self.connect(tray, QtCore.SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), onTrayIconActivated)

        # Set up GUI
        self.setObjectName('QMainWindow')
        self.setWindowTitle(self.APP_NAME)

        self._thermalGPU = ThermalUnitWidget(self, tempMinMax= (0, 95), tempColorLimits= self.GPU_COLOR_LIMITS, fanMinMax= (0, 5500), sliderMaxAndTick= (120, 20))
        self._thermalGPU.setTitle('GPU')
        self._thermalCPU = ThermalUnitWidget(self, tempMinMax= (0, 110), tempColorLimits= self.CPU_COLOR_LIMITS, fanMinMax= (0, 5500), sliderMaxAndTick= (120, 20))
        self._thermalCPU.setTitle('CPU')

        # Say where the numbers come from: the Dell sensor is a firmware/board sensor, not
        # an Intel package reading, and the GPU number comes from the NVIDIA driver.
        self._thermalGPU.setSourceNote(
            'GPU temperature: NVIDIA NVML (driver)' if self._gpuTemp.available
            else 'GPU temperature: Dell firmware sensor (WMI)')
        self._thermalCPU.setSourceNote(
            'CPU temperature: Dell firmware sensor 1. Verified on this board: 63 °C idle → 85 °C '
            'under a 10-process load. This is a board sensor, not an Intel package reading.')

        # Auto mode fan curve: CPU temp -> fan speed %
        # 50 °C  -> 3500 RPM (~64 % of ~5500 max)
        # 80 °C+ -> 100 % (max RPM)
        # Linear interpolation between, clamped.        self._autoCurveMinTemp = 50
        self._autoCurveMaxTemp = 80
        self._autoCurveMinRpm = 3500
        self._autoCurveMaxRpm = 5500

        # Detecting GPU/CPU model is a slow operation, run asynchronously
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
                print("DetectCpuGpuModelsWorker: started")
                d = DetectHardware()
                gpuModel = d.getHardwareName(d.GPUFanIdx)
                cpuModel = d.getHardwareName(d.CPUFanIdx)
                print(f"DetectCpuGpuModelsWorker: finished: {gpuModel}, {cpuModel}")
                self.finished.emit(gpuModel, cpuModel)
            def start(self):
                self._t.start()
        detect = DetectCpuGpuModelsWorker(self, self.updateGaugeTitles)
        detect.start()

        lTherm = QtWidgets.QHBoxLayout()
        lTherm.addWidget(self._thermalGPU)
        lTherm.addWidget(self._thermalCPU)

        self._modeSwitch = QRadioButtonSet(None, None, list(map(lambda m: (m.name.replace('_', ' '), m.value), MODE_ORDER)))

        # Fail-safe indicator
        failsafeIndicator = QtWidgets.QLabel()
        def updFailsafeIndicator() -> None:
            color = Colors.GREEN.value if self._failsafeOn else Colors.DARK_GREY.value
            msg = "Normal"
            if self._failsafeTempIsHighTs > 0: # Fail-safe have tripped at some point in the past
                color = Colors.YELLOW.value
                timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._failsafeTempIsHighTs))
                msg = f"Last high temp at {timeStr}"
                if self._failsafeTrippedPrevModeStr is not None: # Fail-safe is in tripped state now
                    color = Colors.RED.value

            failsafeIndicator.setStyleSheet(f"QLabel {{ min-height: 14px; min-width: 14px; max-height: 14px; max-width: 14px; border: 1px solid {Colors.GREY.value}; border-radius: 7px; background: {color}; }}")
            failsafeIndicator.setToolTip(msg)
        updFailsafeIndicator()

        # Fail-safe temp limits
        self._limitTempGPU = QtWidgets.QComboBox()
        self._limitTempGPU.addItems(list(map(lambda v: str(v), range(50, 91))))
        self._limitTempGPU.setToolTip("Threshold GPU temp")
        self._limitTempCPU = QtWidgets.QComboBox()
        self._limitTempCPU.addItems(list(map(lambda v: str(v), range(50, 101))))
        self._limitTempCPU.setToolTip("Threshold CPU temp")
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
        self._failsafeCB.setToolTip(f"Switch to G-mode (fans on max) when GPU temp reaches {self.FAILSAFE_GPU_TEMP}°C or CPU reaches {self.FAILSAFE_CPU_TEMP}°C")
        def onFailsafeCB():
            self._failsafeOn = self._failsafeCB.isChecked()
            self._failsafeTempIsHighTs = 0
            self._failsafeTrippedPrevModeStr = None
            self._failsafeTempIsHighStartTs = None
            updFailsafeIndicator()
        self._failsafeCB.toggled.connect(onFailsafeCB)
        self._failsafeCB.setChecked(self._failsafeOn)

        failsafeBox = QtWidgets.QHBoxLayout()
        failsafeBox.addWidget(self._failsafeCB)
        failsafeBox.addWidget(self._limitTempGPU)
        failsafeBox.addWidget(self._limitTempCPU)
        failsafeBox.addWidget(failsafeIndicator)

        modeBox = QtWidgets.QHBoxLayout()
        modeBox.addWidget(self._modeSwitch, alignment= QtCore.Qt.AlignLeft)
        modeBox.addStretch(1)

        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.addLayout(lTherm)
        # One row per control group: the mode switch used to share a row with the fail-safe
        # widgets, which pushed the last mode off the window edge.
        mainLayout.addLayout(modeBox)
        mainLayout.addLayout(failsafeBox)
        mainLayout.setAlignment(QtCore.Qt.AlignTop)
        mainLayout.setContentsMargins(10, 0, 10, 0)
        self.adjustSize()

        # Glue GUI to backend
        self.gModeHotKey = None
        self._updateGaugesTask = None

        def setFanSpeed(fan: Literal['GPU', 'CPU'], speed: int) -> None:
            res = self._awcc.setFanSpeed(self._awcc.GPUFanIdx if fan == 'GPU' else self._awcc.CPUFanIdx, speed)
            print(f'Set {fan} fan speed to {speed}: ' + ('ok' if res else 'fail'))

        def updateFanSpeed():
            if self._modeSwitch.getChecked() not in (ThermalMode.Custom.value, ThermalMode.Auto.value):
                return
            setFanSpeed('GPU', self._thermalGPU.getSpeedSlider())
            setFanSpeed('CPU', self._thermalCPU.getSpeedSlider())
        self._thermalGPU.speedSliderChanged(updateFanSpeed)
        self._thermalCPU.speedSliderChanged(updateFanSpeed)

        self._lastGoodMode = ThermalMode.Balanced.value

        def onModeChange(val: str):
            self._thermalGPU.setSpeedDisabled(val != (ThermalMode.Custom.value, ThermalMode.Auto.value))
            self._thermalCPU.setSpeedDisabled(val != ThermalMode.Custom.value)
            res = self._awcc.setMode(self._awcc.Mode[val])
            print(f'Set mode {val}: ' + ('ok' if res else 'fail'))
            if not res:
                if val in (ThermalMode.Quiet.value, ThermalMode.Performance.value):
                    # This firmware doesn't know the mode (verified: G15 5530 answers -1
                    # to 150/152 but 0 to the USTT ids). Drop the option instead of dying.
                    print(f'Mode {val} is not supported here, hiding it')
                    self._modeSwitch.setOptionEnabled(val, False)
                    self._modeSwitch.setChecked(self._lastGoodMode)
                    self.toasterMessage(["Not supported", f"This firmware has no {val} profile", "Thermal mode"])
                    return
                self._errorExit(f"Failed to set mode {val}", "Program is terminated")
            self._lastGoodMode = val
            updateFanSpeed()
            if val != ThermalMode.G_Mode.value:
                self._failsafeTrippedPrevModeStr = None # In case the mode was switched manually
            updFailsafeIndicator()
            for m in ThermalMode:
                self._trayMenuModeSwitch[m.value].setText(f"{'•' if m.value == val else ' '} {m.name.replace('_', ' ')}")

        self._modeSwitch.setChecked(ThermalMode.Balanced.value)
        onModeChange(ThermalMode.Balanced.value)
        self._modeSwitch.setOnChange(onModeChange)

        def updateAppState():
            # Get temps and RPMs
            self._touchHeartbeat()
            # NVML reads the driver directly and is not affected by the bogus WMI GPU
            # readings (#9). Fall back to the Dell sensor when there is no NVIDIA driver.
            nvmlGpu = self._gpuTemp.read()
            gpuTemp = self._saneTemp(nvmlGpu if nvmlGpu is not None
                                    else self._awcc.getFanRelatedTemp(self._awcc.GPUFanIdx))
            gpuRPM = self._awcc.getFanRPM(self._awcc.GPUFanIdx)
            cpuTemp = self._saneTemp(self._awcc.getFanRelatedTemp(self._awcc.CPUFanIdx))
            cpuRPM = self._awcc.getFanRPM(self._awcc.CPUFanIdx)
            # Update UI gauges
            if gpuTemp is not None: self._thermalGPU.setTemp(gpuTemp)
            if gpuRPM is not None: self._thermalGPU.setFanRPM(gpuRPM)
            if cpuTemp is not None: self._thermalCPU.setTemp(cpuTemp)
            if cpuRPM is not None: self._thermalCPU.setFanRPM(cpuRPM)
            # print(gpuTemp, gpuRPM, cpuTemp, cpuRPM)

            # Handle fail-safe
            # Dell's driver intermittently reports 2-3 °C (also when the dGPU is asleep, #9), so a
            # single bogus reading must not trip the fail-safe - but a sensor that stays silent must.
            now = time.time()
            self._cpuUnknownSince = None if cpuTemp is not None else (self._cpuUnknownSince or now)
            self._gpuUnknownSince = None if gpuTemp is not None else (self._gpuUnknownSince or now)
            def sensorGone(ts: Optional[float]) -> bool:
                return ts is not None and now - ts > self.FAILSAFE_UNKNOWN_GRACE_SEC
            tempIsHigh = (
                (cpuTemp is not None and cpuTemp >= self.FAILSAFE_CPU_TEMP) or
                (gpuTemp is not None and gpuTemp >= self.FAILSAFE_GPU_TEMP) or
                sensorGone(self._cpuUnknownSince) or sensorGone(self._gpuUnknownSince)
            )
            
            if tempIsHigh:
                self._failsafeTempIsHighTs = time.time()

            self._failsafeTempIsHighStartTs = (self._failsafeTempIsHighStartTs or time.time()) if tempIsHigh else None

            # Trip fail-safe
            if (self._failsafeOn and 
                self._modeSwitch.getChecked() != ThermalMode.G_Mode.value and
                tempIsHigh and
                time.time() - self._failsafeTempIsHighStartTs > self.FAILSAFE_TRIGGER_DELAY_SEC
            ):
                self._failsafeTrippedPrevModeStr = self._modeSwitch.getChecked()
                self._modeSwitch.setChecked(ThermalMode.G_Mode.value)
                self._toasterMessageCurrentMode(source='failsafe')
                print(f'Fail-safe tripped at GPU={gpuTemp} CPU={cpuTemp}')

            # Auto-reset failsafe
            if (self._failsafeTrippedPrevModeStr is not None and
                time.time() - self._failsafeTempIsHighTs > self.FAILSAFE_RESET_AFTER_TEMP_IS_OK_FOR_SEC
            ):
                self._modeSwitch.setChecked(self._failsafeTrippedPrevModeStr)
                self._toasterMessageCurrentMode(source='failsafe')
                self._failsafeTrippedPrevModeStr = None
                print('Fail-safe reset')

            # Auto mode: fan speed follows CPU temperature curve
            # 50 °C -> 3500 RPM, 80 °C+ -> max RPM (5500), linear between
            if self._modeSwitch.getChecked() == ThermalMode.Auto.value and cpuTemp is not None:
                if cpuTemp <= self._autoCurveMinTemp:
                    targetRpm = self._autoCurveMinRpm
                elif cpuTemp >= self._autoCurveMaxTemp:
                    targetRpm = self._autoCurveMaxRpm
                else:
                    t = (cpuTemp - self._autoCurveMinTemp) / (self._autoCurveMaxTemp - self._autoCurveMinTemp)
                    targetRpm = int(self._autoCurveMinRpm + t * (self._autoCurveMaxRpm - self._autoCurveMinRpm))
                pct = int(round(targetRpm / self._autoCurveMaxRpm * 100))
                pct = max(0, min(100, pct))
                self._awcc.setFanSpeed(self._awcc.CPUFanIdx, pct)
                self._awcc.setFanSpeed(self._awcc.GPUFanIdx, pct)
                # Update sliders to show current auto speed
                self._thermalCPU.setSpeedSlider(pct)
                self._thermalGPU.setSpeedSlider(pct)

            # Update tray icon
            self.trayIcon = self.trayIcon.resizeForScreen() or self.trayIcon
            self.trayIcon.update((gpuTemp, cpuTemp), self._modeSwitch.getChecked() == ThermalMode.G_Mode.value)
            tray.setIcon(self.trayIcon)
            tray.setToolTip(f"GPU:    {gpuTemp} °C    {gpuRPM} RPM\nCPU:    {cpuTemp} °C    {cpuRPM} RPM\nMode:    {self._modeSwitch.getChecked().replace('_', ' ')}")
            
            # Poll slower while the window is hidden: 21 wakeups/s was the baseline debt
            self._updateGaugesTask.setInterval(
                self.TEMP_UPD_PERIOD_MS if self.isVisible() else self.TEMP_UPD_PERIOD_MS_HIDDEN)

            # Periodically save app settings
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

    def updateGaugeTitles(self, gpuModel, cpuModel):
        if gpuModel: self._thermalGPU.setTitle(gpuModel)
        if cpuModel: self._thermalCPU.setTitle(cpuModel)

    def closeEvent(self, event):
        minimizeOnClose = self.settings.value(SettingsKey.MinimizeOnCloseFlag.value)
        if minimizeOnClose is not None:
            minimizeOnClose = str(minimizeOnClose).lower() == 'true'
        
        if minimizeOnClose is None:
            # minimizeOnClose is not set, prompt user
            (toExit, dontAskAgain) = confirm("Exit", "Do you want to exit or minimize to tray?", ("Exit", "Minimize"), True)
            minimizeOnClose = not toExit
            if dontAskAgain:
                self.settings.setValue(SettingsKey.MinimizeOnCloseFlag.value, minimizeOnClose)

        if minimizeOnClose:
            event.ignore()
            self.hide()
        else:
            self.onExit()
        return

    # onExit() connected to systray_Exit
    def onExit(self):
        print("exit")
        # Set mode to Balanced before exit
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
        # Stop the watchdog only after the mode was restored, so it cannot race us.
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

        # Launch through WMI so the watchdog is not a child of this process: a force-kill
        # with /T (Task Manager, taskkill /T) would otherwise take the watchdog down with us.
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
        sourceStr = f" [Fail-safe]" if source == 'failsafe' else ""
        self.toasterMessage(
            [
                self._modeSwitch.getChecked().replace('_', ' '),
                f"GPU: {self._thermalGPU.getTemp()}°C, CPU: {self._thermalCPU.getTemp()}°C",
                "Thermal mode changed" + sourceStr
            ],
            source != 'failsafe'
        )

    def toasterMessage(self, message: List[str | None], expire = True) -> None:
        toast = Toast(duration=ToastDuration.Short, expiration_time= (datetime.datetime.now() + datetime.timedelta(seconds=5)) if expire else None)
        toast.text_fields = message
        toast.AddImage(ToastDisplayImage.fromPath(resourcePath(GUI_ICON)))
        self._toaster.show_toast(toast)

    @staticmethod
    def _saneTemp(t: Optional[int]) -> Optional[int]:
        # Implausible readings are "no data", not 2 °C (Dell driver bug, issue #9)
        return t if isinstance(t, int) and 5 <= t <= 120 else None

    def _saveAppSettings(self):
        # G-mode is a temporary boost, so remember the mode the user picked before it
        modeToSave = self._modeSwitch.getChecked()
        if modeToSave == ThermalMode.G_Mode.value:
            modeToSave = self._gModeKeyPrevModeStr or ThermalMode.Balanced.value
        curValues = [
            modeToSave,
            self._thermalCPU.getSpeedSlider(),
            self._thermalGPU.getSpeedSlider(),
            self.FAILSAFE_CPU_TEMP,
            self.FAILSAFE_GPU_TEMP,
            self._failsafeOn
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

    def _loadAppSettings(self):
        savedMode = self.settings.value(SettingsKey.Mode.value)
        # G-mode is a temporary boost, not a preference: restoring it at boot is why the
        # machine came back up with the fans screaming (issue #92).
        if savedMode not in [m.value for m in ThermalMode] or savedMode == ThermalMode.G_Mode.value:
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

    def clearAppSettings(self):
        (isYes, _) = confirm("Reset to Default", "Do you want to reset all settings to default?", ("Reset", "Cancel"))
        if not isYes: return
        self.settings.clear()
        self._loadAppSettings()

    def G_Mode_key_Pressed(self, val):
        print("G_Mode_key " + str(val))

def runApp(startMinimized = False) -> int:
    app = QtWidgets.QApplication([])

    # Setup backend
    try:
        awcc = AWCCThermal()
    except NoAWCCWMIClass:
        errorExit("AWCC WMI class not found in the system.", "You don't have some drivers installed or your system is not supported.")
    except CannotInstAWCCWMI:
        errorExit("Couldn't instantiate AWCC WMI class.", "Make sure you're running as Admin.")

    # Refuse models we never tested: an unknown board may answer different mode ids, and a
    # wrong mode id here means a fan curve we cannot reason about.
    try:
        model = DetectHardware().getModelName()
    except Exception:
        model = None
    if not DetectHardware.isSupportedModel(model) and not DetectHardware.isUnsupportedAllowed():
        errorExit(
            "This laptop model is not verified.",
            f"Detected: {model}\n\nThis fork was only tested on: {', '.join(SUPPORTED_MODELS)}.\n"
            f"If you want to try anyway, set the environment variable {ALLOW_UNSUPPORTED_ENV}=1."
            f"Wrong thermal settings can overheat a machine that uses a different firmware interface."
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
            border-radius: 3;
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
            spacing: 6px;
            padding: 1px 2px;
        }}
        QRadioButton::indicator {{
            width: 12px;
            height: 12px;
            border-radius: 7px;
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

    # The style sheet above changes font metrics (bold when checked), so the window has to be
    # re-fitted after it is applied - otherwise the mode row ends up outside the window.
    mainWindow.adjustSize()

    if startMinimized:
        mainWindow.showMinimized()
        mainWindow.hide()
    else:
        mainWindow.show()

    return app.exec()