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
if enable_logging:
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Allow overriding log location via environment variables.
    # - UBA_LOG_FILE: full path to log file
    # - UBA_LOG_DIR: directory where uba.log will be created
    log_file = os.environ.get("UBA_LOG_FILE", "").strip()
    log_dir = os.environ.get("UBA_LOG_DIR", "").strip()
    if not log_file:
        log_file = os.path.join(log_dir, "uba.log") if log_dir else "uba.log"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
    except Exception:
        pass

    logHandler = handlers.TimedRotatingFileHandler(log_file, when='D', interval=1, backupCount=0)
    logHandler.setLevel(logging.DEBUG)
    logHandler.setFormatter(fmt)
    logger.addHandler(logHandler)
    # Also log to stderr so it is visible when running from a terminal.
    streamHandler = logging.StreamHandler()
    streamHandler.setLevel(logging.INFO)
    streamHandler.setFormatter(fmt)
    logger.addHandler(streamHandler)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Make freezes debuggable:
    # 1) `kill -USR1 <pid>` will dump stack traces of all threads into uba.log
    # 2) If Python crashes with an uncaught exception, it will be logged too.
    try:
        _fh = open(os.path.abspath(log_file), "a", buffering=1, encoding="utf-8")
        faulthandler.enable(file=_fh, all_threads=True)
        faulthandler.register(signal.SIGUSR1, file=_fh, all_threads=True, chain=False)
    except Exception:
        pass

    try:
        # Record a few env vars that commonly affect GUI behavior.
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
        logger.info("Logging enabled. log_file=%s", os.path.abspath(log_file))
        for k in env_keys:
            v = os.environ.get(k)
            if v is not None and v != "":
                logger.info("env %s=%s", k, v)
    except Exception:
        pass
else:
    logger.addHandler(logging.NullHandler())

def global_excepthook(type, value, tb):
    logger.error("Uncaught exception", exc_info=(type, value, tb))
    # Use the exception passed to the hook; traceback.format_exc() can be empty here.
    print("".join(traceback.format_exception(type, value, tb)))

sys.excepthook = global_excepthook
