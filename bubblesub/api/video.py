from PyQt5 import QtCore


class VideoApi(QtCore.QObject):
    loaded = QtCore.pyqtSignal([])
    seek_requested = QtCore.pyqtSignal([int])
    playback_requested = QtCore.pyqtSignal([object, object])
    pause_requested = QtCore.pyqtSignal([])

    def __init__(self):
        super().__init__()
        self._timecodes = []
        self._path = None
        self._is_paused = False
        self._current_pts = None

    def seek(self, pts):
        self.seek_requested.emit(pts)

    def play(self, start, end):
        self.playback_requested.emit(start, end)

    def unpause(self):
        self.playback_requested.emit(None, None)

    def pause(self):
        self.pause_requested.emit()

    @property
    def current_pts(self):
        return self._current_pts

    @current_pts.setter
    def current_pts(self, new_pts):
        self._current_pts = new_pts

    @property
    def is_paused(self):
        return self._is_paused

    @is_paused.setter
    def is_paused(self, paused):
        self._is_paused = paused

    @property
    def path(self):
        return self._path

    @property
    def timecodes(self):
        return self._timecodes



