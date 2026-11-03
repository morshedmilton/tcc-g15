# (c) github.com/AlexIII
# GPLv3

import sys, os, tempfile, ctypes
from GUI.AppGUI import runApp, errorExit

def isUserAdmin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def requestAdminElevation() -> bool:
    if isUserAdmin():
        return True
    try:
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        if ret > 32:
            return True
    except Exception:
        pass
    return False

def createAppLockFile():
    basename = (
        os.path.splitext(os.path.abspath(sys.argv[0]))[0]
            .replace("/", "-").replace(":", "").replace("\\", "-")
            + ".lock"
    )
    lockfile = os.path.normpath(tempfile.gettempdir() + "/" + basename)
    if os.path.exists(lockfile):
        try:
            os.unlink(lockfile)
        except OSError:
            pass
    try:
        os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
    except OSError:
        pass

def main():
    if not isUserAdmin() and not getattr(sys, 'frozen', False):
        if requestAdminElevation():
            return 0

    try:
        createAppLockFile()
    except Exception:
        errorExit("Another instance of this app is already running")
        return 1

    startMinimized = "--minimized" in sys.argv
    return runApp(startMinimized)

if __name__ == "__main__":
    print("Starting")
    sys.exit(main())
