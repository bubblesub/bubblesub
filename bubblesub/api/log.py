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

"""Logging API."""

import contextlib
import datetime
import enum
import traceback
from collections.abc import Iterator

from PyQt5 import QtCore

from bubblesub.cfg import Config


class LogLevel(enum.Enum):
    """Message log level."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    COMMAND_ECHO = "cmd-echo"


class LogApi(QtCore.QObject):
    """The logging API."""

    logged = QtCore.pyqtSignal(LogLevel, str)

    def __init__(self, cfg: Config) -> None:
        """Initialize self.

        :param cfg: program configuration
        """
        super().__init__()
        self._cfg = cfg

    def debug(self, text: str) -> None:
        """Log a message with debug level.

        :param text: text to log
        """
        self.log(LogLevel.DEBUG, text)

    def info(self, text: str) -> None:
        """Log a message with info level.

        :param text: text to log
        """
        self.log(LogLevel.INFO, text)

    def warn(self, text: str) -> None:
        """Log a message with warning level.

        :param text: text to log
        """
        self.log(LogLevel.WARNING, text)

    def error(self, text: str) -> None:
        """Log a message with error level.

        :param text: text to log
        """
        self.log(LogLevel.ERROR, text)

    def command_echo(self, text: str) -> None:
        """Log a message with command echo level.

        :param text: text to log
        """
        self.log(LogLevel.COMMAND_ECHO, text)

    def log(self, level: LogLevel, text: str) -> None:
        """Log a message.

        :param level: level to log the message with
        :param text: text to log
        """
        for line in text.rstrip("\n").split("\n"):
            if level.value in self._cfg.opt["basic"]["log_levels"]:
                print(
                    f"{datetime.datetime.now()} "
                    f"[{level.name.lower()[0]}] "
                    f"{line}"
                )
            self.logged.emit(level, line)

    @contextlib.contextmanager
    def exception_guard(self) -> Iterator[None]:
        """Eats exceptions and logs then as an error.

        :return: context manager
        """
        try:
            yield
        except Exception as ex:  # pylint: disable=broad-except
            self.error(str(ex))
            self.error(traceback.format_exc())
