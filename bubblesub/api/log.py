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

import enum

from PyQt5 import QtCore


class LogLevel(enum.Enum):
    """Message log level."""

    Error = 1
    Warning = 2
    Info = 3
    Debug = 4
    CommandEcho = 5


class LogApi(QtCore.QObject):
    """The logging API."""

    logged = QtCore.pyqtSignal(LogLevel, str)

    def debug(self, text: str) -> None:
        """
        Log a message with debug level.

        :param text: text to log
        """
        self.log(LogLevel.Debug, text)

    def info(self, text: str) -> None:
        """
        Log a message with info level.

        :param text: text to log
        """
        self.log(LogLevel.Info, text)

    def warn(self, text: str) -> None:
        """
        Log a message with warning level.

        :param text: text to log
        """
        self.log(LogLevel.Warning, text)

    def error(self, text: str) -> None:
        """
        Log a message with error level.

        :param text: text to log
        """
        self.log(LogLevel.Error, text)

    def command_echo(self, text: str) -> None:
        """
        Log a message with command echo level.

        :param text: text to log
        """
        self.log(LogLevel.CommandEcho, text)

    def log(self, level: LogLevel, text: str) -> None:
        """
        Log a message.

        :param level: level to log the message with
        :param text: text to log
        """
        for line in text.split("\n"):
            self.logged.emit(level, line)
