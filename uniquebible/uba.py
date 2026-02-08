#!/usr/bin/env python3

import os, sys, subprocess, platform, ctypes
from shutil import copyfile

# When running this file directly from the source tree, ensure the repo root is
# on sys.path before any `uniquebible.*` imports. Otherwise Python may pick up a
# shadowing namespace package from site-packages (missing `__init__.py`), which
# breaks `from uniquebible import ...` imports.
_this_dir = os.path.dirname(os.path.realpath(__file__))
_repo_root = os.path.dirname(_this_dir)
if _repo_root and _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from uniquebible.install.module import *

# requires python 3.7+
if sys.version_info < (3, 7):
    print("Required python version [3.7 or above] is not found!")
    print("Closing ...")
    exit(1)

def main():
    # set enviornment variables
    os.environ["PYTHONUNBUFFERED"] = "1"

    # check running mode and initial command
    runMode = sys.argv[1] if len(sys.argv) > 1 else ""
    enableCli = True if runMode.lower() in ("stream", "cli", "cli.py", "gui", "terminal", "docker", "telnet-server", "http-server", "execute-macro", "api-server", "api-client", "api-client-localhost") else False
    initialCommand = input("Enter command: ").strip() if runMode == "-i" else " ".join(sys.argv[1:]).strip()
    initialCommand = initialCommand.strip()

    # set working directory
    thisFile = os.path.realpath(__file__)
    wd = os.path.dirname(thisFile)

    thisOS = platform.system()
    if thisOS == "Windows":
        myappid = "uniquebible.app"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        icon_path = os.path.abspath(os.path.join(sys.path[0], "htmlResources", "UniqueBibleApp.ico"))
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(icon_path)

    # Always reuse the same interpreter that is running this script.
    # Using only the basename (e.g. "python") breaks when UBA is installed
    # into a virtualenv but the virtualenv is not activated (PATH mismatch).
    python = sys.executable
    mainModule = f"{__package__}.main" if __package__ else "uniquebible.main"
    mainFile = os.path.join(wd, "main.py")
    #major, minor, micro, *_ = sys.version_info
    cpu = ""
    if thisOS == "Darwin":
        thisOS = "macOS"
        *_, cpu = platform.mac_ver()
        cpu = f"_{cpu}"
    #venvDir = "venv_{0}{4}_{1}.{2}.{3}".format(thisOS, major, minor, micro, cpu)
    #binDir = "Scripts" if thisOS == "Windows" else "bin"

    # create shortcut files
    if not runMode.lower() in ("stream", "terminal", "docker", "telnet-server", "http-server", "execute-macro", "api-server", "api-client", "api-client-localhost"):
        print("Creating shortcut files ...")
        # On Windows
        if thisOS == "Windows":
            desktopPath = os.path.join(os.path.expanduser('~'), 'Desktop')
            shortcutDir = desktopPath if os.path.isdir(desktopPath) else wd
            # gui mode shortcut
            shortcutBat1 = os.path.join(shortcutDir, "UniqueBibleApp.bat")
            shortcutCommand1 = f'''powershell.exe -NoExit -Command "python '{thisFile}'"'''
            # terminal mode shortcut
            shortcutBat2 = os.path.join(shortcutDir, "UniqueBibleAppTerminal.bat")
            shortcutCommand2 = f'''powershell.exe -NoExit -Command "python '{thisFile}' terminal"'''
            windowsShortcuts = {
                shortcutBat1: shortcutCommand1,
                shortcutBat2: shortcutCommand2,
            }
            # Create .bat for application shortcuts
            for shortcutBat, shortcutCommand in windowsShortcuts.items():
                if not os.path.isfile(shortcutBat):
                    try:
                        with open(shortcutBat, "w") as fileObj:
                            fileObj.write(shortcutCommand)
                    except:
                        pass
        # On non-Windows platforms
        else:
            # Create application shortcuts and set file permission
            shortcutSh = os.path.join(wd, "uba.sh")
            if not os.path.exists(shortcutSh):
                # Create .sh shortcut
                with open(shortcutSh, "w") as fileObj:
                    fileObj.write("#!{0}\n{1} {2} gui".format(os.environ["SHELL"], sys.executable, thisFile))
                # Set permission
                for file in (thisFile, "main.py", "util/BibleVerseParser.py", "util/RegexSearch.py", shortcutSh):
                    try:
                        os.chmod(file, 0o755)
                    except:
                        pass
        # desktop shortcut on macOS
        # on iOS a-Shell app, ~/Desktop/ is invalid
        if thisOS == "macOS" and os.path.isdir("~/Desktop/"):
            app = "UniqueBibleApp"
            shortcut_file = os.path.expanduser(f"~/Desktop/{app}.command")
            if not os.path.isfile(shortcut_file):
                thisFile = os.path.realpath(__file__)
                wd = os.path.dirname(thisFile)
                appFile = "uba.py"
                icon_path = os.path.abspath(os.path.join("htmlResources", f"{app}.icns"))
                with open(shortcut_file, "w") as f:
                    f.write("#!/bin/bash\n")
                    f.write(f"cd {wd}\n")
                    f.write(f"{python} {appFile} gui\n")
                os.chmod(shortcut_file, 0o755)
        # desktop shortcuts on Linux
        elif thisOS == "Linux":
            def desktopFileContent():
                iconPath = os.path.join(wd, "htmlResources", "UniqueBibleApp.png")
                return """#!/usr/bin/env xdg-open

[Desktop Entry]
Version=1.0
Type=Application
Terminal=false
Path={0}
Exec={1} {2} gui
Icon={3}
Name=Unique Bible App
""".format(wd, sys.executable, thisFile, iconPath)

            ubaLinuxDesktopFile = os.path.join(wd, "UniqueBibleApp.desktop")
            if not os.path.exists(ubaLinuxDesktopFile):
                # Create .desktop shortcut
                with open(ubaLinuxDesktopFile, "w") as fileObj:
                    fileObj.write(desktopFileContent())
                try:
                    # Try to copy the newly created .desktop file to:
                    from pathlib import Path
                    # ~/.local/share/applications
                    userAppDir = os.path.join(str(Path.home()), ".local", "share", "applications")
                    userAppDirShortcut = os.path.join(userAppDir, "UniqueBibleApp.desktop")
                    if not os.path.exists(userAppDirShortcut):
                        Path(userAppDir).mkdir(parents=True, exist_ok=True)
                        copyfile(ubaLinuxDesktopFile, userAppDirShortcut)
                    # ~/Desktop
                    homeDir = os.environ["HOME"]
                    desktopPath = f"{homeDir}/Desktop"
                    desktopPathShortcut = os.path.join(desktopPath, "UniqueBibleApp.desktop")
                    if os.path.exists(desktopPath) and not os.path.exists(desktopPathShortcut):
                        copyfile(ubaLinuxDesktopFile, desktopPathShortcut)
                except:
                    pass

    # Run main.py
    if thisOS == "Windows":
        if enableCli:
            exec("from uniquebible.main import *", globals())
        else:
            subprocess.Popen([python, "-m", mainModule, initialCommand] if initialCommand else [python, "-m", mainModule])
    else:
        # Run main.py
        if enableCli:
            #os.system("{0} {1}{2}".format(python, mainFile, f" {initialCommand}" if initialCommand else ""))
            exec("from uniquebible.main import *", globals())
        else:
            subprocess.Popen([python, "-m", mainModule, initialCommand] if initialCommand else [python, "-m", mainModule])

def gui():
    sys.argv.insert(1, "gui")
    main()

def stream():
    sys.argv.insert(1, "stream")
    main()

def api():
    # web api-client, not api-server mode
    sys.argv.insert(1, "api-client")
    main()

def apil():
    # web api-client, not api-server mode; connect to localhost
    sys.argv.insert(1, "api-client-localhost")
    main()

def http():
    sys.argv.insert(1, "http-server")
    main()

def ssh():
    sys.argv.insert(1, "ssh-server")
    main()

def telnet():
    sys.argv.insert(1, "telnet-server")
    main()

def term():
    sys.argv.insert(1, "terminal")
    main()

if __name__ == '__main__':
    main()
