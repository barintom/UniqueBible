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
    logHandler = handlers.TimedRotatingFileHandler('uba.log', when='D', interval=1, backupCount=0)
    logHandler.setLevel(logging.DEBUG)
    logger.addHandler(logHandler)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Make freezes debuggable:
    # 1) `kill -USR1 <pid>` will dump stack traces of all threads into uba.log
    # 2) If Python crashes with an uncaught exception, it will be logged too.
    try:
        _fh = open(os.path.abspath("uba.log"), "a", buffering=1, encoding="utf-8")
        faulthandler.enable(file=_fh, all_threads=True)
        faulthandler.register(signal.SIGUSR1, file=_fh, all_threads=True, chain=False)
    except Exception:
        pass
else:
    logger.addHandler(logging.NullHandler())

def global_excepthook(type, value, tb):
    logger.error("Uncaught exception", exc_info=(type, value, tb))
    # Use the exception passed to the hook; traceback.format_exc() can be empty here.
    print("".join(traceback.format_exception(type, value, tb)))

sys.excepthook = global_excepthook
