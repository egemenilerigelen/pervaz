"""Sürecin kurulumu: log, Windows kimliği, QApplication ve tek kopya kilidi."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from pervaz import __version__
from pervaz.app.controller import AppController
from pervaz.core.platform.appid import set_app_user_model_id
from pervaz.core.platform.single_instance import acquire_single_instance
from pervaz.identity import APP_DISPLAY_NAME, APP_NAME, APP_USER_MODEL_ID
from pervaz.infra import paths
from pervaz.infra.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging(paths.log_dir())
    logger.info("%s %s başlatılıyor", APP_NAME, __version__)
    set_app_user_model_id(APP_USER_MODEL_ID)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setApplicationVersion(__version__)

    lock = acquire_single_instance(paths.lock_file())
    if lock is None:
        QMessageBox.information(
            None, APP_DISPLAY_NAME, "Uygulama zaten çalışıyor (sistem tepsisine bakın)."
        )
        return 0

    controller = AppController(app)
    controller.start()
    exit_code = app.exec()
    lock.unlock()
    return exit_code
