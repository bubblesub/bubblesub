# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import asyncio
import sys
import traceback as tb
import types
from typing import Any, Optional

import quamash
from PyQt5.QtCore import Qt, QThread, pyqtRemoveInputHook
from PyQt5.QtGui import QPaintEvent, QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen

from bubblesub.api import Api
from bubblesub.api.log import LogLevel
from bubblesub.cfg import ConfigError
from bubblesub.ui.assets import ASSETS_DIR
from bubblesub.ui.main_window import MainWindow


class MySplashScreen(QSplashScreen):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._painted = False

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        self._painted = True

    def showMessage(self, text: str) -> None:
        self._painted = False
        super().showMessage(text, Qt.AlignBottom, Qt.white)
        self._ensure_painted()

    def _ensure_painted(self) -> None:
        while not self._painted:
            QThread.usleep(1000)
            QApplication.processEvents()


class Logger:
    def __init__(self, api: Api) -> None:
        self._api = api
        self._main_window: Optional[MainWindow] = None
        self._queued_logs: list[tuple["LogLevel", str]] = []

        sys.excepthook = self._on_error
        api.log.logged.connect(self._on_log)

    def set_main_window(self, main_window: MainWindow) -> None:
        self._main_window = main_window
        for log_level, text in self._queued_logs:
            self._on_log(log_level, text)
        self._queued_logs.clear()

    def _on_log(self, level: LogLevel, text: str) -> None:
        if self._main_window:
            self._main_window.console.log_window.log(level, text)
        else:
            self._queued_logs.append((level, text))

    def _on_error(
        self,
        type_: type[BaseException],
        value: BaseException,
        traceback: types.TracebackType,
    ) -> None:
        self._api.log.error("An unhandled error occurred: ")
        self._api.log.error(
            "".join(tb.format_exception(type_, value, traceback))
        )


class Application:
    def __init__(self, args: argparse.Namespace):
        self._args = args
        self._splash: Optional[QSplashScreen] = None

        pyqtRemoveInputHook()

        self._app = QApplication(sys.argv)
        self._app.setApplicationName("bubblesub")
        self._loop = quamash.QEventLoop(self._app)
        asyncio.set_event_loop(self._loop)

    def splash_screen(self) -> None:
        pixmap = QPixmap(str(ASSETS_DIR / "bubblesub.png"))
        pixmap = pixmap.scaledToWidth(640)
        self._splash = MySplashScreen(pixmap)
        self._splash.show()
        self._splash.showMessage("Loading API...")

    def run(self, api: Api) -> None:
        with self._loop:
            logger = Logger(api)

            try:
                if self._splash:
                    self._splash.showMessage("Loading config...")
                if not self._args.no_config:
                    api.cfg.load(api.cfg.DEFAULT_PATH)
            except ConfigError as ex:
                api.log.error(str(ex))

            if self._splash:
                self._splash.showMessage("Loading commands...")
            api.cmd.reload_commands()

            if self._splash:
                self._splash.showMessage("Loading UI...")
            main_window = MainWindow(api)
            api.gui.set_main_window(main_window)
            logger.set_main_window(main_window)

            # load empty file
            api.subs.unload()

            main_window.show()

            def save_config() -> None:
                if not self._args.no_config:
                    assert api.cfg.root_dir is not None
                    api.cfg.save(api.cfg.root_dir)

            api.cfg.opt.changed.connect(save_config)

            if self._args.file:
                api.cmd.run_cmdline([["open", "--path", self._args.file]])

            if self._splash:
                self._splash.finish(main_window)

            self._loop.run_forever()

        save_config()
