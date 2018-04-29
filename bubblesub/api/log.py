"""Logging API."""
import enum

import bubblesub.event


class LogLevel(enum.Enum):
    """Message log level."""

    Error = 1
    Warning = 2
    Info = 3
    Debug = 4


class LogApi:
    """The logging API."""

    logged = bubblesub.event.EventHandler(LogLevel, str)

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
