import ffms
from PyQt5 import QtCore

import bubblesub.util


class TimecodesProviderContext(bubblesub.util.ProviderContext):
    def __init__(self, log_api):
        super().__init__()
        self._log_api = log_api

    def work(self, task):
        path = task
        self._log_api.info('video/timecodes: loading... ({})'.format(path))

        path_hash = bubblesub.util.hash_digest(path)
        cache_name = f'index-{path_hash}-video'

        result = bubblesub.util.load_cache(cache_name)
        if result:
            timecodes, keyframes = result
        else:
            video = ffms.VideoSource(str(path))
            timecodes = video.track.timecodes
            keyframes = video.track.keyframes
            bubblesub.util.save_cache(cache_name, (timecodes, keyframes))

        self._log_api.info('video/timecodes: loaded')
        return path, timecodes, keyframes


class TimecodesProvider(bubblesub.util.Provider):
    def __init__(self, parent, log_api):
        super().__init__(parent, TimecodesProviderContext(log_api))


class VideoApi(QtCore.QObject):
    timecodes_updated = QtCore.pyqtSignal()

    def __init__(self, media_api, log_api):
        super().__init__()

        self._media_api = media_api
        self._media_api.loaded.connect(self._on_media_load)

        self._timecodes = []
        self._keyframes = []

        self._timecodes_provider = TimecodesProvider(self, log_api)
        self._timecodes_provider.finished.connect(self._got_timecodes)

    def get_opengl_context(self):
        return self._media_api._mpv.opengl_cb_api()

    def screenshot(self, path, include_subtitles):
        self._media_api._mpv.command(
            'screenshot-to-file',
            path,
            'subtitles' if include_subtitles else 'video')

    def align_pts_to_next_frame(self, pts):
        if self.timecodes:
            for timecode in self.timecodes:
                if timecode >= pts:
                    return timecode
        return pts

    @property
    def timecodes(self):
        return self._timecodes

    @property
    def keyframes(self):
        return self._keyframes

    def _on_media_load(self):
        self._timecodes = []
        self._keyframes = []

        self.timecodes_updated.emit()

        if self._media_api.is_loaded:
            self._timecodes_provider.schedule_task(self._media_api.path)

    def _got_timecodes(self, result):
        path, timecodes, keyframes = result
        if path == self._media_api.path:
            self._timecodes = timecodes
            self._keyframes = keyframes
            self.timecodes_updated.emit()
