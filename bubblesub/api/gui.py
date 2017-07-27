from PyQt5 import QtCore


class GuiApi(QtCore.QObject):
    quit_requested = QtCore.pyqtSignal([])
    begin_update_requested = QtCore.pyqtSignal([])
    end_update_requested = QtCore.pyqtSignal([])

    def __init__(self):
        super().__init__()
        self.main_window = None

    def quit(self):
        self.quit_requested.emit()

    def begin_update(self):
        self.begin_update_requested.emit()

    def end_update(self):
        self.end_update_requested.emit()
