from pathlib import Path
import ffms
import bubblesub.util
from PyQt5 import QtCore


class TimecodesProviderContext(bubblesub.util.ProviderContext):
    def __init__(self, log_api):
        super().__init__()
        self._log_api = log_api

    def work(self, task):
        path = task
        self._log_api.info('timecodes: loading... ({})'.format(path))
        cache_key = str(path)
        timecodes = bubblesub.util.load_cache('index', cache_key)
        if not timecodes:
            video = ffms.VideoSource(str(path))
            timecodes = video.track.timecodes
            bubblesub.util.save_cache('index', cache_key, timecodes)
        self._log_api.info('timecodes: loaded')
        return path, timecodes


class TimecodesProvider(bubblesub.util.Provider):
    def __init__(self, parent, log_api):
        super().__init__(parent, TimecodesProviderContext(log_api))


class VideoApi(QtCore.QObject):
    loaded = QtCore.pyqtSignal()
    seek_requested = QtCore.pyqtSignal(int)
    playback_requested = QtCore.pyqtSignal([object, object])
    pause_requested = QtCore.pyqtSignal()
    timecodes_updated = QtCore.pyqtSignal()
    pos_changed = QtCore.pyqtSignal()
    playback_speed_changed = QtCore.pyqtSignal(float)

    def __init__(self, log_api):
        super().__init__()
        self._timecodes = []
        self._path = None
        self._is_paused = False
        self._current_pts = None
        self._playback_speed = 1

        self._timecodes_provider = TimecodesProvider(self, log_api)
        self._timecodes_provider.finished.connect(self._got_timecodes)

    def seek(self, pts):
        self.seek_requested.emit(pts)

    def play(self, start, end):
        self.playback_requested.emit(start, end)

    def unpause(self):
        self.playback_requested.emit(None, None)

    def pause(self):
        self.pause_requested.emit()

    @property
    def playback_speed(self):
        return self._playback_speed

    @playback_speed.setter
    def playback_speed(self, speed):
        self._playback_speed = speed
        self.playback_speed_changed.emit(speed)

    @property
    def current_pts(self):
        return self._current_pts

    @current_pts.setter
    def current_pts(self, new_pts):
        self._current_pts = new_pts
        self.pos_changed.emit()

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

    def unload(self):
        self._path = None
        self._timecodes = []
        self.timecodes_updated.emit()
        self.loaded.emit()

    def load(self, path):
        assert path
        self._path = Path(path)
        self._timecodes = []
        self.timecodes_updated.emit()
        self._timecodes_provider.schedule(self._path)
        self.loaded.emit()

    def _got_timecodes(self, result):
        path, timecodes = result
        if path == self.path:
            self._timecodes = timecodes
            self.timecodes_updated.emit()
