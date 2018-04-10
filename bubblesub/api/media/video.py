import typing as T
from pathlib import Path

import ffms
from PyQt5 import QtCore

import bubblesub.cache
import bubblesub.provider
import bubblesub.util
import bubblesub.api.media.media
import bubblesub.api.log


class TimecodesProviderResult:
    def __init__(
            self,
            path: Path,
            timecodes: T.List[int],
            keyframes: T.List[int],
    ) -> None:
        self.path = path
        self.timecodes = timecodes
        self.keyframes = keyframes


class TimecodesProviderContext(
        bubblesub.provider.ProviderContext[Path, TimecodesProviderResult]
):
    def __init__(self, log_api: 'bubblesub.api.log.LogApi') -> None:
        super().__init__()
        self._log_api = log_api

    def work(self, task: Path) -> TimecodesProviderResult:
        path = task
        self._log_api.info('video/timecodes: loading... ({})'.format(path))

        path_hash = bubblesub.util.hash_digest(path)
        cache_name = f'index-{path_hash}-video'

        result = bubblesub.cache.load_cache(cache_name)
        if result:
            timecodes, keyframes = result
        else:
            video = ffms.VideoSource(str(path))
            timecodes = video.track.timecodes
            keyframes = video.track.keyframes
            bubblesub.cache.save_cache(cache_name, (timecodes, keyframes))

        self._log_api.info('video/timecodes: loaded')
        return TimecodesProviderResult(path, timecodes, keyframes)


class TimecodesProvider(bubblesub.provider.Provider[TimecodesProviderContext]):
    def __init__(
            self,
            parent: QtCore.QObject,
            log_api: 'bubblesub.api.log.LogApi',
    ) -> None:
        super().__init__(parent, TimecodesProviderContext(log_api))


class VideoApi(QtCore.QObject):
    timecodes_updated = QtCore.pyqtSignal()

    def __init__(
            self,
            media_api: 'bubblesub.api.media.media.MediaApi',
            log_api: 'bubblesub.api.log.LogApi',
    ) -> None:
        super().__init__()

        self._media_api = media_api
        self._media_api.loaded.connect(self._on_media_load)

        self._timecodes: T.List[int] = []
        self._keyframes: T.List[int] = []

        self._timecodes_provider = TimecodesProvider(self, log_api)
        self._timecodes_provider.finished.connect(self._got_timecodes)

    def get_opengl_context(self) -> T.Any:
        return self._media_api._mpv.opengl_cb_api()

    def screenshot(self, path: Path, include_subtitles: bool) -> None:
        self._media_api._mpv.command(
            'screenshot-to-file',
            path,
            'subtitles' if include_subtitles else 'video')

    def align_pts_to_next_frame(self, pts: int) -> int:
        if self.timecodes:
            for timecode in self.timecodes:
                if timecode >= pts:
                    return timecode
        return pts

    @property
    def timecodes(self) -> T.List[int]:
        return self._timecodes

    @property
    def keyframes(self) -> T.List[int]:
        return self._keyframes

    def _on_media_load(self) -> None:
        self._timecodes = []
        self._keyframes = []

        self.timecodes_updated.emit()

        if self._media_api.is_loaded:
            self._timecodes_provider.schedule_task(self._media_api.path)

    def _got_timecodes(self, result: TimecodesProviderResult) -> None:
        if result.path == self._media_api.path:
            self._timecodes = result.timecodes
            self._keyframes = result.keyframes
            self.timecodes_updated.emit()
