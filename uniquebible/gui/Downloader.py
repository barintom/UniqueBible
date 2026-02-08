import os, zipfile, platform, subprocess, sys
from uniquebible import config
import logging, time
# import threading
if config.qtLibrary == "pyside6":
    from PySide6.QtWidgets import QGridLayout, QPushButton, QDialog, QLabel
    from PySide6.QtCore import QObject, Signal, QTimer
else:
    from qtpy.QtWidgets import QGridLayout, QPushButton, QDialog, QLabel
    from qtpy.QtCore import QObject, Signal, QTimer
from uniquebible.install.module import *


class DownloadProcess(QObject):

    finished = Signal()

    def __init__(self, cloudFile, localFile):
        super().__init__()
        self.cloudFile, self.localFile = cloudFile, localFile

    def downloadFile(self):
        # Prefer running gdown as a subprocess. In practice this keeps the Qt UI more responsive
        # than calling the Python API directly (less GIL contention during large downloads).
        logger = logging.getLogger("uba")
        t0 = time.monotonic()
        logger.info("DownloadProcess: start cloudFile=%s localFile=%s", self.cloudFile, self.localFile)
        try:
            if not config.gdownIsUpdated:
                installmodule("--upgrade gdown")
                config.gdownIsUpdated = True
            try:
                # Ensure gdown cookie file is writable in restricted environments.
                cookie_file = os.path.join(getattr(config, "ubaUserDir", os.path.expanduser("~")), "temp", "gdown_cookies.txt")
                os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
                env = os.environ.copy()
                env.setdefault("GDOWN_COOKIE_FILE", cookie_file)

                proc = subprocess.run(
                    [sys.executable, "-m", "gdown", self.cloudFile, "-O", self.localFile, "--quiet"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                )
                if proc.returncode == 0 and os.path.isfile(self.localFile):
                    print("Downloaded " + self.localFile)
                    logger.info("DownloadProcess: gdown ok (%.2fs) file=%s", time.monotonic() - t0, self.localFile)
                    connection = True
                else:
                    if proc.stderr:
                        print(proc.stderr)
                        logger.warning("DownloadProcess: gdown failed rc=%s stderr=%s", proc.returncode, proc.stderr.strip())
                    connection = False
            except Exception as ex:
                print(ex)
                logger.exception("DownloadProcess: gdown exception")
                connection = False
        except Exception as ex:
            print("Failed to download '{0}'!".format(self.cloudFile))
            print(ex)
            logger.exception("DownloadProcess: outer exception")
            connection = False
        if connection and os.path.isfile(self.localFile) and self.localFile.endswith(".zip"):
            # Extract in a subprocess. Zip extraction is CPU-heavy Python code and can still
            # starve the Qt UI due to the GIL even when called from a QThread.
            t_extract = time.monotonic()
            logger.info("DownloadProcess: extracting zip (subprocess) file=%s", self.localFile)
            path, *_ = os.path.split(self.localFile)
            extract_code = (
                "import os, zipfile\n"
                f"zf={self.localFile!r}\n"
                f"out={path!r}\n"
                "with zipfile.ZipFile(zf,'r') as z: z.extractall(out)\n"
                "try: os.remove(zf)\n"
                "except Exception: pass\n"
            )
            proc = subprocess.run(
                [sys.executable, "-c", extract_code],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if proc.returncode != 0 and proc.stderr:
                print(proc.stderr)
                logger.warning("DownloadProcess: extract failed rc=%s stderr=%s", proc.returncode, proc.stderr.strip())
            else:
                logger.info("DownloadProcess: extract ok (%.2fs)", time.monotonic() - t_extract)
        if config.downloadGCloudModulesInSeparateThread:
            # Emit a signal to notify that download process is finished
            logger.info("DownloadProcess: finished signal (%.2fs total)", time.monotonic() - t0)
            self.finished.emit()


class Downloader(QDialog):

    def __init__(self, parent, databaseInfo):
        super().__init__()
        self.parent = parent
        self.setWindowTitle(config.thisTranslation["message_downloadHelper"])
        # When downloading in a separate thread, don't block the whole UI.
        self.setModal(not config.downloadGCloudModulesInSeparateThread)

        self.databaseInfo = databaseInfo
        fileItems, *_ = databaseInfo
        self.filename = fileItems[-1]

        self.setupLayout()

    def setupLayout(self):

        self.messageLabel = QLabel("{1} '{0}'".format(self.filename, config.thisTranslation["message_missing"]))

        self.downloadButton = QPushButton(config.thisTranslation["message_install"])
        self.downloadButton.clicked.connect(self.startDownloadFile)

        self.cancelButton = QPushButton(config.thisTranslation["message_cancel"])
        self.cancelButton.clicked.connect(self.close)

        self.remarks = QLabel("{0} {1}".format(config.thisTranslation["message_remarks"], config.thisTranslation["message_downloadAllFiles"]))

        self.layout = QGridLayout()
        self.layout.addWidget(self.messageLabel, 0, 0)
        self.layout.addWidget(self.downloadButton, 1, 0)
        if config.downloadGCloudModulesInSeparateThread:
            self.layout.addWidget(self.cancelButton, 2, 0)
        self.layout.addWidget(self.remarks, 3, 0)
        self.setLayout(self.layout)

    def startDownloadFile(self):
        self.setWindowTitle(config.thisTranslation["message_installing"])
        self.messageLabel.setText(config.thisTranslation["message_installing"])
        self.downloadButton.setText(config.thisTranslation["message_installing"])
        self.downloadButton.setEnabled(False)
        if config.downloadGCloudModulesInSeparateThread:
            self.cancelButton.setText(config.thisTranslation["runInBackground"])
        # Allow the dialog to repaint before starting the (potentially long) work.
        QTimer.singleShot(0, lambda: self.downloadFile(True))

    # Put in a separate funtion to allow downloading file without gui
    def downloadFile(self, notification=True):
        self.parent.downloadFile(self.databaseInfo, notification)
