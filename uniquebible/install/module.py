import shlex
import subprocess
import sys

def installmodule(module, update=True):
    # Always install using the same interpreter that is running UBA.
    # This makes installs work even when a venv isn't activated (PATH mismatch).
    pip_base = [sys.executable, "-m", "pip"]

    try:
        subprocess.run(pip_base + ["-V"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception:
        print("pip command is not found!")
        return False

    if update:
        from uniquebible import config
        if not config.pipIsUpdated:
            try:
                update_proc = subprocess.run(
                    pip_base + ["install", "--upgrade", "pip", "--no-input"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if update_proc.returncode == 0:
                    print("pip tool updated!")
                else:
                    print("pip tool failed to be updated!")
                    if update_proc.stderr:
                        print(update_proc.stderr)
            except Exception:
                print("pip tool failed to be updated!")
            config.pipIsUpdated = True

    try:
        print("Installing '{0}' ...".format(module))
        install_proc = subprocess.run(
            pip_base + ["install", "--no-cache-dir", "--no-input", *shlex.split(module)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if install_proc.returncode == 0:
            print("Module '{0}' is installed!".format(module))
            return True

        # pip uses stderr for a lot of output; only show it when the install fails.
        if install_proc.stderr:
            print(install_proc.stderr)
        elif install_proc.stdout:
            print(install_proc.stdout)
        return False
    except Exception:
        return False
