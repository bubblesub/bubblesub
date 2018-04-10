import enum

from PyQt5 import QtCore


class LogLevel(enum.Enum):
    Error = 1
    Warning = 2
    Info = 3
    Debug = 4


class LogApi(QtCore.QObject):
    logged = QtCore.pyqtSignal(object, str)

    def debug(self, text: str) -> None:
        self.log(LogLevel.Debug, text)

    def info(self, text: str) -> None:
        self.log(LogLevel.Info, text)

    def warn(self, text: str) -> None:
        self.log(LogLevel.Warning, text)

    def error(self, text: str) -> None:
        self.log(LogLevel.Error, text)

    def log(self, level: LogLevel, text: str) -> None:
        self.logged.emit(level, text)
