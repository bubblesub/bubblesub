"""Logging API."""
import enum

from PyQt5 import QtCore


class LogLevel(enum.Enum):
    """Message log level."""

    Error = 1
    Warning = 2
    Info = 3
    Debug = 4


class LogApi(QtCore.QObject):
    """The logging API."""

    logged = QtCore.pyqtSignal(object, str)

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

    def log(self, level: LogLevel, text: str) -> None:
        """
        Log a message.

        :param level: level to log the message with
        :param text: text to log
        """
        self.logged.emit(level, text)
