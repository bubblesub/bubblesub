from PyQt5 import QtWidgets


class Video(QtWidgets.QFrame):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self._api = api
        self._api.video.connect_presenter(int(self.winId()))
        self._api.video.pause()
        # TODO: buttons for play/pause like aegisub
