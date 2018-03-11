import enum

from PyQt5 import QtCore


class LogLevel(enum.Enum):
    Error = 1
    Warning = 2
    Info = 3
    Debug = 4


class LogApi(QtCore.QObject):
    logged = QtCore.pyqtSignal(object, str)

    def debug(self, *args, **kwargs):
        self.log(LogLevel.Debug, *args, **kwargs)

    def info(self, *args, **kwargs):
        self.log(LogLevel.Info, *args, **kwargs)

    def warn(self, *args, **kwargs):
        self.log(LogLevel.Warning, *args, **kwargs)

    def error(self, *args, **kwargs):
        self.log(LogLevel.Error, *args, **kwargs)

    def log(self, level, text):
        self.logged.emit(level, text)
