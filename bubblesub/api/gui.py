from PyQt5 import QtCore


class GuiApi(QtCore.QObject):
    quit_requested = QtCore.pyqtSignal()
    begin_update_requested = QtCore.pyqtSignal()
    end_update_requested = QtCore.pyqtSignal()

    def __init__(self, api):
        super().__init__()
        self._api = api
        self._main_window = None

    def set_main_window(self, main_window):
        self._main_window = main_window

    async def exec(self, func, *args, **kwargs):
        return await func(self._api, self._main_window, *args, **kwargs)

    def quit(self):
        self.quit_requested.emit()

    def begin_update(self):
        self.begin_update_requested.emit()

    def end_update(self):
        self.end_update_requested.emit()
