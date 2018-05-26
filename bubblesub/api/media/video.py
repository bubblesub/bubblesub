# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Video API."""

import threading
import time
import typing as T
from pathlib import Path

import ffms
import mpv  # pylint: disable=wrong-import-order
import numpy as np
from PyQt5 import QtCore

import bubblesub.api.log
import bubblesub.api.media.media
import bubblesub.cache
import bubblesub.util
import bubblesub.worker
from bubblesub.api.media.state import MediaState

_LOADING = object()
_SAMPLER_LOCK = threading.Lock()
_PIX_FMT = [ffms.get_pix_fmt('rgb24')]


class VideoSourceWorker(bubblesub.worker.Worker):
    """Detached video source provider."""

    def __init__(self, log_api: 'bubblesub.api.log.LogApi') -> None:
        """
        Initialize self.

        :param log_api: logging API
        """
        super().__init__()
        self._log_api = log_api

    def _do_work(self, task: T.Any) -> T.Any:
        """
        Create video source.

        :param task: path to the video file
        :return: video source
        """
        path = T.cast(Path, task)
        self._log_api.info(f'video/sampler: loading... ({path})')

        if not path.exists():
            self._log_api.error('video/sampler: video file not found')
            return None

        video_source = ffms.VideoSource(str(path))
        self._log_api.info('video/sampler: loaded')
        return (path, video_source)


class VideoApi(QtCore.QObject):
    """The video API."""

    parsed = QtCore.pyqtSignal()

    def __init__(
            self,
            media_api: 'bubblesub.api.media.media.MediaApi',
            log_api: 'bubblesub.api.log.LogApi',
            mpv_: mpv.Context
    ) -> None:
        """
        Initialize self.

        :param media_api: media API
        :param log_api: logging API
        :param mpv_: mpv context
        """
        super().__init__()

        self._media_api = media_api
        self._media_api.state_changed.connect(self._on_media_state_change)
        self._mpv = mpv_

        self._video_source: T.Union[None, ffms.VideoSource] = None
        self._video_source_worker = VideoSourceWorker(log_api)
        self._video_source_worker.task_finished.connect(self._got_video_source)

        self._last_output_fmt: T.Any = None

    def start(self) -> None:
        """Start internal worker threads."""
        self._video_source_worker.start()

    def stop(self) -> None:
        """Stop internal worker threads."""
        self._video_source_worker.stop()

    def get_opengl_context(self) -> T.Any:
        """
        Return internal player's OpenGL context usable by the GUI.

        :return: OpenGL context
        """
        return self._mpv.opengl_cb_api()

    def screenshot(self, path: Path, include_subtitles: bool) -> None:
        """
        Save a screenshot into specified destination.

        :param path: path to save the screenshot to
        :param include_subtitles: whether to 'burn in' the subtitles
        """
        self._mpv.command(
            'screenshot-to-file',
            str(path),
            'subtitles' if include_subtitles else 'video'
        )

    def align_pts_to_prev_frame(self, pts: int) -> int:
        """
        Align PTS to a frame immediately before given PTS.

        :param pts: PTS to align
        :return: aligned PTS
        """
        if self.timecodes:
            for timecode in reversed(self.timecodes):
                if timecode <= pts:
                    return timecode
        return pts

    def align_pts_to_next_frame(self, pts: int) -> int:
        """
        Align PTS to a frame immediately after given PTS.

        :param pts: PTS to align
        :return: aligned PTS
        """
        if self.timecodes:
            for timecode in self.timecodes:
                if timecode >= pts:
                    return timecode
        return pts

    @property
    def width(self) -> T.Optional[int]:
        """
        Return horizontal video resolution.

        :return: video width in pixels
        """
        try:
            return self._mpv.get_property('width')
        except mpv.MPVError:
            return 0

    @property
    def height(self) -> T.Optional[int]:
        """
        Return vertical video resolution.

        :return: video height in pixels
        """
        try:
            return self._mpv.get_property('height')
        except mpv.MPVError:
            return 0

    @property
    def has_video_source(self) -> bool:
        """
        Return whether video source is available.

        :return: whether video source is available
        """
        return (
            self._video_source is not None
            and self._video_source is not _LOADING
        )

    @property
    def timecodes(self) -> T.List[int]:
        """
        Return video frames' PTS.

        :return: video frames' PTS
        """
        if not self.has_video_source:
            return []
        if not self._wait_for_video_source():
            return []
        return self._video_source.track.timecodes

    @property
    def keyframes(self) -> T.List[int]:
        """
        Return video keyframes' PTS.

        :return: video keyframes' PTS
        """
        if not self.has_video_source:
            return []
        if not self._wait_for_video_source():
            return []
        return self._video_source.track.keyframes

    def get_frame(self, frame_idx: int, width: int, height: int) -> np.array:
        """
        Get raw video data from the currently loaded video source.

        :param frame_idx: frame number
        :param width: output image width
        :param height: output image height
        :return: numpy image
        """
        with _SAMPLER_LOCK:
            if not self.has_video_source \
                    or not self._wait_for_video_source() \
                    or frame_idx < 0 \
                    or frame_idx >= len(self.timecodes):
                return np.zeros(width * height * 3).reshape((width, height, 3))

            new_output_fmt = (_PIX_FMT, width, height, ffms.FFMS_RESIZER_AREA)
            if self._last_output_fmt != new_output_fmt:
                self._video_source.set_output_format(*new_output_fmt)
                self._last_output_fmt = new_output_fmt

            frame = self._video_source.get_frame(frame_idx)
            return (
                frame.planes[0]
                .reshape((height, frame.Linesize[0]))
                [:, 0:width * 3]
                .reshape(height, width, 3)
            )

    def _wait_for_video_source(self) -> bool:
        if self._video_source is None:
            return False
        while self._video_source is _LOADING:
            time.sleep(0.01)
        return True

    def _on_media_state_change(self, state: MediaState) -> None:
        if state == MediaState.Unloaded:
            self._video_source = None
        elif state == MediaState.Loading:
            self._last_output_fmt = None
            self._video_source = _LOADING
            self._video_source_worker.schedule_task(self._media_api.path)
        else:
            assert state == MediaState.Loaded

    def _got_video_source(self, result: T.Optional[ffms.VideoSource]) -> None:
        if result is not None:
            path, video_source = result
            if path == self._media_api.path:
                self._video_source = video_source
                self.parsed.emit()
