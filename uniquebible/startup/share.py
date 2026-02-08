import glob, os, sys, logging, traceback
import signal
import faulthandler
from uniquebible import config
import logging.handlers as handlers
from uniquebible.util.FileUtil import FileUtil


def cleanupTempFiles():
    files = glob.glob(os.path.join("htmlResources", "main-*.html"))
    for file in files:
        os.remove(file)

# Run startup plugins
def runStartupPlugins():
    if config.enablePlugins:
        for ff in (config.packageDir, config.ubaUserDir):
            for plugin in FileUtil.fileNamesWithoutExtension(os.path.join(ff, "plugins", "startup"), "py"):
                if not plugin in config.excludeStartupPlugins:
                    script = os.path.join(ff, "plugins", "startup", "{0}.py".format(plugin))
                    config.mainWindow.execPythonFile(script)

def printContentOnConsole(text):
    if not "html-text" in sys.modules:
        import html_text
    print(html_text.extract_text(text))
    #subprocess.Popen(["echo", html_text.extract_text(text)])
    #sys.stdout.flush()
    return text


# clean up
cleanupTempFiles()

# Setup logging
logger = logging.getLogger('uba')
# Allow enabling logging without editing config.py (useful for debugging crashes).
enable_logging = bool(getattr(config, "enableLogging", False)) or os.environ.get("UBA_ENABLE_LOGGING") == "1"
fmt = logging.Formatter(
    fmt="%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Default log path should be predictable (in the UBA user directory), not dependent on CWD.
# Allow overriding log location via environment variables.
# - UBA_LOG_FILE: full path to log file
# - UBA_LOG_DIR: directory where uba.log will be created
default_log_dir = getattr(config, "ubaUserDir", os.path.join(os.path.expanduser("~"), "UniqueBible"))
log_file = os.environ.get("UBA_LOG_FILE", "").strip()
log_dir = os.environ.get("UBA_LOG_DIR", "").strip()
if not log_file:
    log_file = os.path.join(log_dir, "uba.log") if log_dir else os.path.join(default_log_dir, "uba.log")
try:
    os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
except Exception:
    pass

# Always create the log file handler so errors/freezes have somewhere to go by default.
# When enable_logging is False, keep it quiet (WARNING+ only).
logger.setLevel(logging.DEBUG)
logHandler = handlers.TimedRotatingFileHandler(log_file, when='D', interval=1, backupCount=0)
logHandler.setLevel(logging.DEBUG if enable_logging else logging.WARNING)
logHandler.setFormatter(fmt)
logger.addHandler(logHandler)

# Console logging only when explicitly enabled.
if enable_logging:
    streamHandler = logging.StreamHandler()
    streamHandler.setLevel(logging.INFO)
    streamHandler.setFormatter(fmt)
    logger.addHandler(streamHandler)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

# Make freezes debuggable even when verbose logging is off:
# `kill -USR1 <pid>` dumps stack traces of all threads into the log file.
try:
    _fh = open(os.path.abspath(log_file), "a", buffering=1, encoding="utf-8")
    faulthandler.enable(file=_fh, all_threads=True)
    faulthandler.register(signal.SIGUSR1, file=_fh, all_threads=True, chain=False)
except Exception:
    pass

try:
    env_keys = (
        "UBA_ENABLE_LOGGING",
        "UBA_LOG_FILE",
        "UBA_LOG_DIR",
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "QT_API",
        "QT_QPA_PLATFORM",
        "XDG_SESSION_TYPE",
        "GDK_BACKEND",
        "VIRTUAL_ENV",
        "PYTHONPATH",
    )
    logger.warning("Logging initialized. enable_logging=%s log_file=%s", enable_logging, os.path.abspath(log_file))
    if enable_logging:
        for k in env_keys:
            v = os.environ.get(k)
            if v is not None and v != "":
                logger.info("env %s=%s", k, v)
except Exception:
    pass

def global_excepthook(type, value, tb):
    logger.error("Uncaught exception", exc_info=(type, value, tb))
    # Use the exception passed to the hook; traceback.format_exc() can be empty here.
    print("".join(traceback.format_exception(type, value, tb)))

sys.excepthook = global_excepthook
