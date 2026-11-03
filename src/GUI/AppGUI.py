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

GUI_ICON = 'icons/gaugeIcon.png'
HEARTBEAT_FILE = os.path.join(tempfile.gettempdir(), 'tcc-g15.heartbeat')

def applyWindowsGlassAndDarkTheme(hwnd: int) -> None:
    """Enables Windows 11 DWM dark title bar and Acrylic frosted glass backdrop."""
    try:
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        v = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(v), 4)

        # DWMWA_SYSTEMBACKDROP_TYPE = 38 (3 = Acrylic, 2 = Mica)
        backdrop = ctypes.c_int(3)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop), 4)

        # Extend DWM frame into client area for full client acrylic blur
        class MARGINS(ctypes.Structure):
            _fields_ = [
                ("cxLeftWidth", ctypes.c_int),
                ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int),
                ("cyBottomHeight", ctypes.c_int),
            ]
        margins = MARGINS(-1, -1, -1, -1)
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
    except Exception:
        pass

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

APP_STYLESHEET = """
    QWidget#QMainWindow {
        background: rgba(10, 14, 22, 0.55);
        border: 1px solid rgba(0, 240, 255, 0.35);
        border-top: 2px solid #00F0FF;
        border-radius: 6px;
        font-family: 'Orbitron', 'Cascadia Code', 'Consolas', 'Segoe UI', sans-serif;
    }

    QFrame#CyberCard {
        background: rgba(16, 22, 34, 0.60);
        border: 1px solid rgba(0, 240, 255, 0.25);
        border-top: 2px solid rgba(0, 240, 255, 0.70);
        border-radius: 4px;
    }

    QFrame#CyberDeck {
        background: rgba(14, 18, 28, 0.70);
        border: 1px solid rgba(0, 240, 255, 0.28);
        border-top: 1px solid rgba(255, 255, 255, 0.20);
        border-bottom: 2px solid #FCEE0A;
        border-radius: 4px;
    }

    QPushButton#CyberSafeButton {
        background: rgba(20, 26, 38, 0.65);
        border: 1px solid rgba(0, 255, 102, 0.35);
        border-radius: 3px;
        padding: 2px 4px;
    }
    QPushButton#CyberSafeButton:hover {
        background: rgba(0, 255, 102, 0.22);
        border: 1px solid #00FF66;
    }

    /* Cyberpunk Fan Offset Slider with #00FF66 -> #FCEE0A -> #FF003C Neon Gradient */
    QSlider::groove:horizontal {
        height: 4px;
        background: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(0, 240, 255, 0.25);
        border-radius: 1px;
    }
    QSlider::sub-page:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00FF66, stop:0.65 #FCEE0A, stop:1 #FF003C);
    }
    QSlider::sub-page:horizontal:disabled {
        background: rgba(255, 255, 255, 0.05);
    }
    QSlider::handle:horizontal {
        background: #FCEE0A;
        border: 1px solid #FFFFFF;
        width: 10px;
        margin-top: -5px;
        margin-bottom: -5px;
        border-radius: 2px;
    }
    QSlider::handle:horizontal:hover {
        background: #FFFFFF;
        border-color: #00F0FF;
    }
    QSlider::handle:horizontal:disabled {
        background: #3A4252;
        border-color: transparent;
    }

    QToolTip {
        background: rgba(12, 16, 24, 0.96);
        color: #00F0FF;
        border: 1px solid rgba(0, 240, 255, 0.40);
        border-radius: 2px;
        padding: 4px 6px;
        font-family: 'Orbitron', 'Cascadia Code', monospace;
        font-size: 10px;
    }
"""


class CyberSafeButton(QtWidgets.QPushButton):
    """Tactical Safeguard PushButton with proper child layout size hinting to prevent clipping."""
    def sizeHint(self) -> QtCore.QSize:
        if self.layout():
            layout_hint = self.layout().sizeHint()
            return QtCore.QSize(max(114, layout_hint.width() + 8), max(24, layout_hint.height()))
        return super().sizeHint()

    def minimumSizeHint(self) -> QtCore.QSize:
        if self.layout():
            layout_min = self.layout().minimumSize()
            return QtCore.QSize(max(114, layout_min.width() + 8), max(24, layout_min.height()))
        return super().minimumSizeHint()


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
    APP_VERSION = "1.8.2"
    APP_DESCRIPTION = "Open-source, liquid-efficient thermal control for Dell G15."
    APP_URL = "github.com/morshedmilton/tcc-g15"
    APP_CREDITS = "Original app & research: github.com/AlexIII/tcc-g15\nMaintained fork for Dell G15 5530: github.com/morshedmilton/tcc-g15"

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

        self.settings = QtCore.QSettings(self.APP_URL, "AWCC")

        self.setWindowIcon(QtGui.QIcon(resourcePath(GUI_ICON)))
        self.mouseReleaseEvent = lambda evt: (
            evt.button() == QtCore.Qt.RightButton and
            alert("About", f"{self.APP_NAME} v{self.APP_VERSION}", message2=f"{self.APP_DESCRIPTION}\n\n{self.APP_CREDITS}")
        )

        # Set up tray menu
        self.trayIcon = QGaugeTrayIcon((self.GPU_COLOR_LIMITS, self.CPU_COLOR_LIMITS))
        menu = QtWidgets.QMenu()
        menu.addSection("Mode")
        self._trayMenuModeSwitch = {}
        for m in MODE_ORDER:
            modeAction = menu.addAction("-")
            modeAction.triggered.connect(lambda _, m_value=m.value: self._modeSwitch.setChecked(m_value))
            self._trayMenuModeSwitch[m.value] = modeAction

        menu.addSection("Power Automation")
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
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet(APP_STYLESHEET)

        # Thermal Unit Widgets
        self._thermalGPU = ThermalUnitWidget(self, tempMinMax=(0, 95), tempColorLimits=self.GPU_COLOR_LIMITS, fanMinMax=(0, 5500), sliderMaxAndTick=(100, 20), hardwareType='GPU')
        self._thermalGPU.setTitle('GPU')
        self._thermalCPU = ThermalUnitWidget(self, tempMinMax=(0, 110), tempColorLimits=self.CPU_COLOR_LIMITS, fanMinMax=(0, 5500), sliderMaxAndTick=(100, 20), hardwareType='CPU')
        self._thermalCPU.setTitle('CPU')

        self._thermalGPU.setSourceNote(
            'GPU: NVIDIA NVML (direct driver)' if self._gpuTemp.available
            else 'GPU: Dell WMI sensor 6')
        self._thermalCPU.setSourceNote(
            'CPU: Dell WMI sensor 1 (firmware board reading)')

        # Detect GPU/CPU models asynchronously
        class DetectCpuGpuModelsWorker(QtCore.QObject):
            finished = QtCore.Signal(str, str)
            def __init__(self, parent: QtCore.QObject, on_result: Callable[[Optional[str], Optional[str]], None]) -> None:
                super().__init__()
                self._t = QtCore.QThread(parent)
                self.moveToThread(self._t)
                self.finished.connect(self._t.quit)
                self.finished.connect(on_result)
                self._t.started.connect(self._task)

            def _task(self):
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                    try:
                        d = DetectHardware()
                        gpuModel = d.getHardwareName(d.GPUFanIdx) or ""
                        cpuModel = d.getHardwareName(d.CPUFanIdx) or ""
                        self.finished.emit(gpuModel, cpuModel)
                    finally:
                        pythoncom.CoUninitialize()
                except Exception as ex:
                    import logging
                    logging.getLogger("tcc-g15").warning("Hardware detection worker failed: %s", ex)

            def start(self):
                if not self._t.isRunning():
                    self._t.start()

        detect = DetectCpuGpuModelsWorker(self, self.updateGaugeTitles)
        self._detectWorker = detect
        detect.start()

        # Top row: 2 Frosted Glass Thermal Cards
        lTherm = QtWidgets.QHBoxLayout()
        lTherm.setContentsMargins(0, 0, 0, 0)
        lTherm.setSpacing(6)
        lTherm.addWidget(self._thermalGPU)
        lTherm.addWidget(self._thermalCPU)

        # Cyberpunk Floating Tactical Deck
        cyberDeck = QtWidgets.QFrame()
        cyberDeck.setObjectName("CyberDeck")
        deckBox = QtWidgets.QHBoxLayout(cyberDeck)
        deckBox.setContentsMargins(6, 4, 6, 4)
        deckBox.setSpacing(4)

        # 1. Cyberpunk Tactical Mode Selector
        self._modeSwitch = QRadioButtonSet(None, None, [(m.name.replace('_', ' '), m.value) for m in MODE_ORDER])
        deckBox.addWidget(self._modeSwitch, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        deckBox.addStretch(1)

        # 2. Tactical Divider
        techDivider = QtWidgets.QFrame()
        techDivider.setFrameShape(QtWidgets.QFrame.VLine)
        techDivider.setStyleSheet("background: rgba(0, 240, 255, 0.35); width: 1px; max-width: 1px; margin: 3px 2px;")
        deckBox.addWidget(techDivider)

        # 3. Tactical Safeguard Module (Fail-Safe)
        self._failsafeBtn = CyberSafeButton()
        self._failsafeBtn.setObjectName("CyberSafeButton")
        self._failsafeBtn.setCursor(QtCore.Qt.PointingHandCursor)
        self._failsafeBtn.setFixedHeight(24)
        self._failsafeBtn.setMinimumWidth(114)

        failsafeInner = QtWidgets.QHBoxLayout(self._failsafeBtn)
        failsafeInner.setContentsMargins(3, 2, 3, 2)
        failsafeInner.setSpacing(2)

        failsafeIndicator = QtWidgets.QLabel("▲")
        failsafeIndicator.setStyleSheet("color: #00FF66; font-size: 9px; font-weight: 900;")
        failsafeLabel = QtWidgets.QLabel("SAFE")
        failsafeLabel.setStyleSheet("color: #FFFFFF; font-family: 'Orbitron', monospace; font-size: 9px; font-weight: 800; letter-spacing: 0.3px;")
        self._failsafeThresholdBadge = QtWidgets.QLabel(f"{self.FAILSAFE_GPU_TEMP}°/{self.FAILSAFE_CPU_TEMP}°")
        self._failsafeThresholdBadge.setStyleSheet("""
            color: #000000;
            background: #FCEE0A;
            font-family: 'Orbitron', monospace;
            font-size: 9px;
            font-weight: bold;
            padding: 1px 3px;
            border-radius: 2px;
        """)

        failsafeInner.addWidget(failsafeIndicator, alignment=QtCore.Qt.AlignVCenter)
        failsafeInner.addWidget(failsafeLabel, alignment=QtCore.Qt.AlignVCenter)
        failsafeInner.addWidget(self._failsafeThresholdBadge, alignment=QtCore.Qt.AlignVCenter)

        def updFailsafeIndicator() -> None:
            color = "#00FF66" if self._failsafeOn else "#4A5262"
            statusText = "ARMED" if self._failsafeOn else "DISARMED"
            self._failsafeThresholdBadge.setText(f"{self.FAILSAFE_GPU_TEMP}°/{self.FAILSAFE_CPU_TEMP}°")
            self._failsafeBtn.updateGeometry()
            msg = f"SAFEGUARD: {statusText} (GPU >= {self.FAILSAFE_GPU_TEMP}°C, CPU >= {self.FAILSAFE_CPU_TEMP}°C)\nClick to toggle. Right-click to calibrate trip limits."

            if self._failsafeTempIsHighTs > 0:
                color = "#FCEE0A"
                msg = f"LAST HIGH THERMAL EVENT: {time.strftime('%H:%M:%S', time.localtime(self._failsafeTempIsHighTs))}"
                if self._failsafeTrippedPrevModeStr is not None:
                    color = "#FF003C"
                    msg = "SAFEGUARD ACTIVE: G-MODE OVERDRIVE ENGAGED"

            failsafeIndicator.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: 900;")
            failsafeLabel.setStyleSheet(f"color: {'#FFFFFF' if self._failsafeOn else '#4A5262'}; font-family: 'Orbitron', monospace; font-size: 10px; font-weight: 800;")
            self._failsafeThresholdBadge.setStyleSheet(
                "color: #000000; background: #FCEE0A; font-family: 'Orbitron', monospace; font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 2px;" if self._failsafeOn
                else "color: #7D8799; background: rgba(255, 255, 255, 0.08); font-family: 'Orbitron', monospace; font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 2px;"
            )
            self._failsafeBtn.setToolTip(msg)

        self._updFailsafeIndicator = updFailsafeIndicator
        updFailsafeIndicator()

        def onFailsafeToggle():
            self._failsafeOn = not self._failsafeOn
            self._failsafeTempIsHighTs = 0
            self._failsafeTrippedPrevModeStr = None
            self._failsafeTempIsHighStartTs = None
            self._failsafeHardTempStartTs = None
            updFailsafeIndicator()

        self._failsafeBtn.clicked.connect(onFailsafeToggle)

        def showThresholdMenu(point):
            menu = QtWidgets.QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background: #0E121C;
                    border: 1px solid #00F0FF;
                    border-radius: 2px;
                    padding: 4px;
                    color: #FFFFFF;
                    font-family: 'Orbitron', 'Cascadia Code', monospace;
                    font-size: 10px;
                }
                QMenu::item {
                    padding: 4px 14px;
                }
                QMenu::item:selected {
                    background: rgba(0, 240, 255, 0.25);
                    color: #FCEE0A;
                }
                QMenu::separator {
                    height: 1px;
                    background: rgba(0, 240, 255, 0.30);
                    margin: 3px 4px;
                }
            """)
            gpuMenu = menu.addMenu(f"GPU TRIP THRESHOLD [{self.FAILSAFE_GPU_TEMP}°C]")
            for gVal in [70, 75, 80, 85, 90]:
                act = gpuMenu.addAction(f"{gVal} °C" + (" [ACTIVE]" if gVal == self.FAILSAFE_GPU_TEMP else ""))
                act.triggered.connect(lambda _, v=gVal: self._setGpuLimit(v))

            cpuMenu = menu.addMenu(f"CPU TRIP THRESHOLD [{self.FAILSAFE_CPU_TEMP}°C]")
            for cVal in [80, 85, 90, 95, 100]:
                act = cpuMenu.addAction(f"{cVal} °C" + (" [ACTIVE]" if cVal == self.FAILSAFE_CPU_TEMP else ""))
                act.triggered.connect(lambda _, v=cVal: self._setCpuLimit(v))

            menu.exec(self._failsafeBtn.mapToGlobal(point))

        self._failsafeBtn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._failsafeBtn.customContextMenuRequested.connect(showThresholdMenu)
        deckBox.addWidget(self._failsafeBtn, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Main window layout: 2 rows only! Compact Cyberpunk HUD Layout
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.setContentsMargins(6, 6, 6, 6)
        mainLayout.setSpacing(5)
        mainLayout.addLayout(lTherm)
        mainLayout.addWidget(cyberDeck)
        mainLayout.setAlignment(QtCore.Qt.AlignTop)

        self.adjustSize()

        # Glue GUI to backend
        self.gModeHotKey = None
        self._updateGaugesTask = None

        def setFanSpeed(fan: Literal['GPU', 'CPU'], speed: int) -> None:
            self._awcc.setFanSpeed(self._awcc.GPUFanIdx if fan == 'GPU' else self._awcc.CPUFanIdx, speed)

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
                return

            res = self._awcc.setMode(modeEnum)
            if not res:
                if val in (ThermalMode.Quiet.value, ThermalMode.Performance.value):
                    self._modeSwitch.setOptionEnabled(val, False)
                    self._modeSwitch.setChecked(self._lastGoodMode)
                    self.toasterMessage(["Not supported", f"Firmware has no {val} profile", "Thermal mode"])
                    return
                self._errorExit(f"Failed to set mode {val}", "Program terminated")

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
            self._ensureWatchdogRunning()

            # NVML direct driver reading
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
                        if currentMode != ThermalMode.Quiet.value:
                            self._acPreferredMode = currentMode
                            self._modeSwitch.setChecked(ThermalMode.Quiet.value)
                            self.toasterMessage(["Battery Mode", "Switched to Quiet profile", "Power Profile"])
                    else:
                        if currentMode == ThermalMode.Quiet.value and self._acPreferredMode:
                            self._modeSwitch.setChecked(self._acPreferredMode)
                            self.toasterMessage(["AC Connected", f"Restored {self._acPreferredMode} profile", "Power Profile"])
                self._isAcPower = ac

            # Fail-Safe Handling
            now = time.time()
            self._cpuUnknownSince = None if cpuTemp is not None else (self._cpuUnknownSince or now)
            self._gpuUnknownSince = None if gpuTemp is not None else (self._gpuUnknownSince or now)
            def sensorGone(ts: Optional[float]) -> bool:
                return ts is not None and (now - ts) > self.FAILSAFE_UNKNOWN_GRACE_SEC

            tempIsHigh = (
                (cpuTemp is not None and cpuTemp >= self.FAILSAFE_CPU_TEMP) or
                (gpuTemp is not None and gpuTemp >= self.FAILSAFE_GPU_TEMP) or
                sensorGone(self._cpuUnknownSince) or sensorGone(self._gpuUnknownSince)
            )

            hardTempIsHigh = (
                (cpuTemp is not None and cpuTemp >= self.FAILSAFE_HARD_CPU_TEMP) or
                (gpuTemp is not None and gpuTemp >= self.FAILSAFE_HARD_GPU_TEMP)
            )

            if tempIsHigh or hardTempIsHigh:
                self._failsafeTempIsHighTs = time.time()

            self._failsafeTempIsHighStartTs = (self._failsafeTempIsHighStartTs or time.time()) if tempIsHigh else None
            self._failsafeHardTempStartTs = (self._failsafeHardTempStartTs or time.time()) if hardTempIsHigh else None

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

            if (self._failsafeTrippedPrevModeStr is not None and
                (time.time() - self._failsafeTempIsHighTs) > self.FAILSAFE_RESET_AFTER_TEMP_IS_OK_FOR_SEC
            ):
                self._modeSwitch.setChecked(self._failsafeTrippedPrevModeStr)
                self._toasterMessageCurrentMode(source='failsafe')
                self._failsafeTrippedPrevModeStr = None

            # Update tray icon
            self.trayIcon = self.trayIcon.resizeForScreen() or self.trayIcon
            self.trayIcon.update((gpuTemp, cpuTemp), self._modeSwitch.getChecked() == ThermalMode.G_Mode.value)
            tray.setIcon(self.trayIcon)
            tray.setToolTip(f"GPU: {gpuTemp or '--'} °C    {gpuRPM or '--'} RPM\nCPU: {cpuTemp or '--'} °C    {cpuRPM or '--'} RPM\nMode: {self._modeSwitch.getChecked().replace('_', ' ')}")

            self._updateGaugesTask.setInterval(
                self.TEMP_UPD_PERIOD_MS if self.isVisible() else self.TEMP_UPD_PERIOD_MS_HIDDEN)

            self._saveAppSettings()

        self._loadAppSettings()

        self._updateAppState = updateAppState
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
        if getattr(self, '_detectWorker', None) is not None:
            try:
                self._detectWorker._t.quit()
                self._detectWorker._t.wait(500)
            except Exception:
                pass
        if getattr(self, '_gpuTemp', None) is not None:
            self._gpuTemp.shutdown()

    def _isWatchdogAlive(self) -> bool:
        if getattr(self, '_watchdog', None) is not None:
            return self._watchdog.poll() is None
        pid = getattr(self, '_watchdogPid', None)
        if pid:
            try:
                import ctypes
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                STILL_ACTIVE = 259
                hProcess = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if not hProcess:
                    return False
                exit_code = ctypes.c_ulong()
                ctypes.windll.kernel32.GetExitCodeProcess(hProcess, ctypes.byref(exit_code))
                ctypes.windll.kernel32.CloseHandle(hProcess)
                return exit_code.value == STILL_ACTIVE
            except Exception:
                return False
        return False

    def _ensureWatchdogRunning(self) -> None:
        if getattr(self, '_watchdogShuttingDown', False):
            return
        if not self._isWatchdogAlive():
            self._startWatchdog()

    def _startWatchdog(self) -> None:
        cmd = watchdogCommand(HEARTBEAT_FILE)
        if not cmd:
            return
        try:
            Path(HEARTBEAT_FILE).write_text('', encoding='utf-8')
        except OSError:
            pass

        try:
            import wmi
            creation = wmi.WMI().Win32_Process.Create(
                CommandLine=' '.join(f'"{part}"' for part in cmd))
            pid = int(creation[1])
            if pid:
                self._watchdogPid = pid
                return
        except Exception:
            pass

        try:
            self._watchdog = subprocess.Popen(cmd, close_fds=True)
        except Exception:
            pass

    def _stopWatchdog(self) -> None:
        self._watchdogShuttingDown = True
        if getattr(self, '_watchdogPid', None):
            try:
                import wmi
                for proc in wmi.WMI().Win32_Process(ProcessId=self._watchdogPid):
                    proc.Terminate()
            except Exception:
                pass
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

    def _setGpuLimit(self, limit: int):
        self.FAILSAFE_GPU_TEMP = limit
        self._updFailsafeIndicator()
        self._saveAppSettings()

    def _setCpuLimit(self, limit: int):
        self.FAILSAFE_CPU_TEMP = limit
        self._updFailsafeIndicator()
        self._saveAppSettings()

    def _loadAppSettings(self):
        savedMode = self.settings.value(SettingsKey.Mode.value)
        if savedMode not in [m.value for m in MODE_ORDER] or savedMode == ThermalMode.G_Mode.value:
            savedMode = ThermalMode.Balanced.value
        self._modeSwitch.setChecked(savedMode)
        savedSpeed = self.settings.value(SettingsKey.CPUFanSpeed.value)
        self._thermalCPU.setSpeedSlider(savedSpeed)
        savedSpeed = self.settings.value(SettingsKey.GPUFanSpeed.value)
        self._thermalGPU.setSpeedSlider(savedSpeed)
        savedTemp = self.settings.value(SettingsKey.CPUThresholdTemp.value)
        if savedTemp is not None and str(savedTemp).isdigit():
            self.FAILSAFE_CPU_TEMP = int(savedTemp)
        savedTemp = self.settings.value(SettingsKey.GPUThresholdTemp.value)
        if savedTemp is not None and str(savedTemp).isdigit():
            self.FAILSAFE_GPU_TEMP = int(savedTemp)
        savedFailsafe = self.settings.value(SettingsKey.FailSafeIsOnFlag.value)
        if savedFailsafe is not None:
            self._failsafeOn = str(savedFailsafe).lower() == 'true'
        self._updFailsafeIndicator()
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
        pass

def runApp(startMinimized=False) -> int:
    app = QtWidgets.QApplication([])

    try:
        awcc = AWCCThermal()
    except NoAWCCWMIClass:
        errorExit("AWCC WMI class not found in the system.", "Driver missing or system unsupported.")
    except CannotInstAWCCWMI:
        errorExit("Couldn't instantiate AWCC WMI class.", "Ensure running as Administrator.")

    try:
        model = DetectHardware().getModelName()
    except Exception:
        model = None
    if not DetectHardware.isSupportedModel(model) and not DetectHardware.isUnsupportedAllowed():
        errorExit(
            "This laptop model is not verified.",
            f"Detected: {model}\n\nSupported: {', '.join(SUPPORTED_MODELS)}.\n"
            f"To override, set {ALLOW_UNSUPPORTED_ENV}=1."
        )

    mainWindow = TCC_GUI(awcc)
    mainWindow.setStyleSheet(APP_STYLESHEET)

    # Apply Windows 11 DWM dark titlebar and Acrylic glass
    applyWindowsGlassAndDarkTheme(int(mainWindow.winId()))

    # Compact window fitting strictly between 360px and 400px
    mainWindow.adjustSize()
    hint = mainWindow.sizeHint()
    targetWidth = max(360, min(400, hint.width()))
    mainWindow.setFixedSize(targetWidth, hint.height())

    if startMinimized:
        mainWindow.showMinimized()
        mainWindow.hide()
    else:
        mainWindow.show()

    return app.exec()
