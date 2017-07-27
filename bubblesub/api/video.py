import ffms
import bubblesub.util
from PyQt5 import QtCore


# TODO: do this somewhere else asynchronously
def _get_timecodes(video_path):
    cache_key = str(video_path)
    timecodes = bubblesub.util.load_cache('index', cache_key)
    if not timecodes:
        print('Reading video time codes, please wait.')
        video = ffms.VideoSource(str(video_path))
        timecodes = video.track.timecodes
        bubblesub.util.save_cache('index', cache_key, timecodes)
    return timecodes


class VideoApi(QtCore.QObject):
    loaded = QtCore.pyqtSignal([])
    seek_requested = QtCore.pyqtSignal([int])
    playback_requested = QtCore.pyqtSignal([object, object])
    pause_requested = QtCore.pyqtSignal([])

    def __init__(self, audio_api):
        super().__init__()
        self._audio_api = audio_api
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

    def load(self, video_path):
        self._path = video_path

        if video_path and video_path.exists():
            # TODO: refactor this
            timecodes = _get_timecodes(video_path)
            self._timecodes = timecodes
            self._audio_api._set_max_pts(timecodes[-1])
        else:
            self._timecodes = []
            self._audio_api._set_max_pts(0)

        self.loaded.emit()

