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

import bisect
import enum
import fractions
import threading
import time
import typing as T
from pathlib import Path

import ffms
import numpy as np
import PIL.Image
from PyQt5 import QtCore

from bubblesub.api.log import LogApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.ass_renderer import AssRenderer
from bubblesub.worker import Worker

_LOADING = object()
_SAMPLER_LOCK = threading.Lock()
_PIX_FMT = [ffms.get_pix_fmt("rgb24")]


class VideoState(enum.Enum):
    NotLoaded = enum.auto()
    Loading = enum.auto()
    Loaded = enum.auto()


class VideoSourceWorker(Worker):
    """Detached video source provider."""

    def __init__(self, log_api: LogApi) -> None:
        """
        Initialize self.

        :param log_api: logging API
        """
        super().__init__()
        self._log_api = log_api

    def _do_work(
        self, task: T.Any
    ) -> T.Tuple[Path, T.Optional[ffms.VideoSource]]:
        """
        Create video source.

        :param task: path to the video file
        :return: video source
        """
        path = T.cast(Path, task)
        self._log_api.info(f"started loading video... ({path})")

        if not path.exists():
            self._log_api.error(f"video file {path} not found")
            return (path, None)

        try:
            source = ffms.VideoSource(str(path))
        except ffms.Error as ex:
            self._log_api.error(f"video couldn't be loaded: {ex}")
            return (path, None)
        else:
            self._log_api.info("video finished loading")
            return (path, source)


class VideoApi(QtCore.QObject):
    """The video API."""

    state_changed = QtCore.pyqtSignal(VideoState)

    def __init__(self, log_api: LogApi, subs_api: SubtitlesApi) -> None:
        """
        Initialize self.

        :param log_api: logging API
        :param subs_api: subtitles API
        """
        super().__init__()
        self._log_api = log_api
        self._subs_api = subs_api

        self._state = VideoState.NotLoaded
        self._path: T.Optional[Path] = None
        self._timecodes: T.List[int] = []
        self._keyframes: T.List[int] = []
        self._frame_rate = 0
        self._width = 0
        self._height = 0

        self._ass_renderer = AssRenderer()
        self._source: T.Union[None, ffms.VideoSource] = None
        self._source_worker = VideoSourceWorker(log_api)
        self._source_worker.task_finished.connect(self._got_source)

        self._last_output_fmt: T.Any = None

        self._source_worker.start()

    def unload(self) -> None:
        """Unload current video source."""
        self._path = None
        self._source = None
        self._timecodes.clear()
        self._keyframes.clear()
        self._width = 0
        self._height = 0
        self._last_output_fmt = None
        self.state = VideoState.NotLoaded

    def load(self, path: T.Union[str, Path]) -> None:
        """
        Load video from specified file.

        :param path: path to load the video from
        """
        self.unload()
        self._path = Path(path)

        self._log_api.info(f"video: loading {path}")
        self.state = VideoState.Loading
        if str(self._subs_api.remembered_video_path) != str(self._path):
            self._subs_api.remembered_video_path = self._path
        self._source_worker.schedule_task(self._path)

    def shutdown(self) -> None:
        """Stop internal worker threads."""
        self._source_worker.stop()

    @property
    def path(self) -> T.Optional[Path]:
        return self._path

    @property
    def state(self) -> VideoState:
        """
        Return current video state.

        :return: video state
        """
        return self._state

    @state.setter
    def state(self, value: VideoState) -> None:
        """
        Set current video state.

        :param value: new video state
        """
        if value != self._state:
            self._log_api.debug(f"video: changed state to {value}")
            self._state = value
            self.state_changed.emit(self._state)

    @property
    def is_ready(self) -> bool:
        """
        Return whether if the video is loaded.

        :return: whether if the video is loaded
        """
        return self._state == VideoState.Loaded

    def screenshot(
        self,
        pts: int,
        path: Path,
        include_subtitles: bool,
        width: T.Optional[int],
        height: T.Optional[int],
    ) -> None:
        """
        Save a screenshot into specified destination.

        :param pts: pts to make screenshot of
        :param path: path to save the screenshot to
        :param include_subtitles: whether to 'burn in' the subtitles
        :param width: optional width to render to
        :param height: optional height to render to
        """

        if not width and not height:
            width = self.width
            height = self.height
        if not width:
            width = int(self.width * height / self.height)
        if not height:
            height = int(self.height * width / self.width)

        pts = self.align_pts_to_prev_frame(pts)
        idx = self.timecodes.index(pts)
        frame = self.get_frame(idx, width, height)
        image = PIL.Image.frombytes("RGB", (width, height), frame)
        if include_subtitles:
            self._ass_renderer.set_source(
                self._subs_api.styles,
                self._subs_api.events,
                self._subs_api.meta,
                (width, height),
            )

            red, green, blue, alpha = self._ass_renderer.render(
                time=pts
            ).split()
            top = PIL.Image.merge("RGB", (red, green, blue))
            mask = PIL.Image.merge("L", (alpha,))
            image.paste(top, (0, 0), mask)
        image.save(str(path))

    def align_pts_to_near_frame(self, pts: int) -> int:
        """
        Align PTS to a frame closest to given PTS.

        :param pts: PTS to align
        :return: aligned PTS
        """
        if self.timecodes:
            max_idx = len(self.timecodes) - 1
            idx1 = max(
                0, min(max_idx, bisect.bisect_right(self.timecodes, pts) - 1)
            )
            idx2 = max(
                0, min(max_idx, bisect.bisect_left(self.timecodes, pts))
            )
            return min(
                [self.timecodes[idx1], self.timecodes[idx2]],
                key=lambda val: abs(val - pts),
            )
        return pts

    def align_pts_to_prev_frame(self, pts: int) -> int:
        """
        Align PTS to a frame immediately before given PTS.

        :param pts: PTS to align
        :return: aligned PTS
        """
        if self.timecodes:
            idx = bisect.bisect_right(self.timecodes, pts) - 1
            if idx >= len(self.timecodes):
                return self.timecodes[-1]
            if pts < self.timecodes[idx]:
                return pts
            return self.timecodes[idx]
        return pts

    def align_pts_to_next_frame(self, pts: int) -> int:
        """
        Align PTS to a frame immediately after given PTS.

        :param pts: PTS to align
        :return: aligned PTS
        """
        if self.timecodes:
            idx = bisect.bisect_left(self.timecodes, pts)
            if idx >= len(self.timecodes):
                return pts
            if pts < 0:
                return self.timecodes[0]
            return self.timecodes[idx]
        return pts

    def frame_idx_from_pts(self, pts: int) -> int:
        """
        Get index of a frame that contains given PTS.

        :param pts: PTS to search for
        :return: frame index, -1 if not found
        """
        if self.timecodes:
            return max(0, bisect.bisect_left(self.timecodes, pts) - 1)
        return -1

    @property
    def frame_rate(self) -> int:
        """
        Return the frame rate.

        :return: video frame rate
        """
        return self._frame_rate

    @property
    def width(self) -> int:
        """
        Return horizontal video resolution.

        :return: video width in pixels
        """
        return self._width

    @property
    def height(self) -> int:
        """
        Return vertical video resolution.

        :return: video height in pixels
        """
        return self._height

    @property
    def timecodes(self) -> T.List[int]:
        """
        Return video frames' PTS.

        :return: video frames' PTS
        """
        if not self._wait_for_source():
            return []
        return self._timecodes

    @property
    def keyframes(self) -> T.List[int]:
        """
        Return video keyframes' indexes.

        :return: video keyframes' indexes
        """
        if not self._wait_for_source():
            return []
        return self._keyframes

    @property
    def min_pts(self) -> int:
        """
        Return minimum video time in milliseconds.

        :return: minimum PTS
        """
        if not self.timecodes:
            return 0
        return self.timecodes[0]

    @property
    def max_pts(self) -> int:
        """
        Return maximum video time in milliseconds.

        :return: maximum PTS
        """
        if not self.timecodes:
            return 0
        return self.timecodes[-1]

    def get_frame(
        self, frame_idx: int, width: int, height: int
    ) -> T.Optional[np.array]:
        """
        Get raw video data from the currently loaded video source.

        :param frame_idx: frame number
        :param width: output image width
        :param height: output image height
        :return: numpy image
        """
        with _SAMPLER_LOCK:
            if (
                not self._wait_for_source()
                or frame_idx < 0
                or frame_idx >= len(self.timecodes)
            ):
                return None
            assert self._source

            new_output_fmt = (_PIX_FMT, width, height, ffms.FFMS_RESIZER_AREA)
            if self._last_output_fmt != new_output_fmt:
                self._source.set_output_format(*new_output_fmt)
                self._last_output_fmt = new_output_fmt

            frame = self._source.get_frame(frame_idx)
            return (
                frame.planes[0]
                .reshape((height, frame.Linesize[0]))[:, 0 : width * 3]
                .reshape(height, width, 3)
            )

    def _got_source(self, result: T.Optional[ffms.VideoSource]) -> None:
        path, source = result
        if path != self._path:
            return

        with _SAMPLER_LOCK:
            self._source = source

            if source is None:
                self.state = VideoState.NotLoaded
                return

            self._timecodes = [
                int(round(pts)) for pts in source.track.timecodes
            ]
            self._keyframes = [idx for idx in source.track.keyframes]
            frame = source.get_frame(0)
            self._width = frame.EncodedWidth
            self._frame_rate = fractions.Fraction(
                self._source.properties.FPSNumerator,
                self._source.properties.FPSDenominator,
            )
            self._height = frame.EncodedHeight
            self._timecodes.sort()
            self._keyframes.sort()
            self.state = VideoState.Loaded

    def _wait_for_source(self) -> bool:
        if self._source is None:
            return False
        while self._source is _LOADING:
            time.sleep(0.01)
        if self._source is None:
            return False
        return True
