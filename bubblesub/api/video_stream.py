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

import asyncio
import bisect
import threading
import uuid
from fractions import Fraction
from pathlib import Path
from typing import Any, ClassVar, Optional, Union, cast

import ffms2
import numpy as np
import PIL.Image
from ass_renderer import AssRenderer
from PyQt5.QtCore import QObject, pyqtBoundSignal, pyqtSignal

from bubblesub.api.base_stream import BaseStream, StreamUnavailable
from bubblesub.api.log import LogApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.api.threading import ThreadingApi

_LOADING = object()
_SAMPLER_LOCK = threading.Lock()
_PIX_FMT = [ffms2.get_pix_fmt("rgb24")]


class VideoStreamUnavailable(StreamUnavailable):
    """Exception raised when trying to access video stream properties when it
    is not fully loaded yet.
    """

    def __init__(self, text: Optional[str] = None) -> None:
        """Initialize self.

        :param text: optional text error
        """
        super().__init__(text or "video stream is not available right now")


def _load_video_source(
    log_api: LogApi, uid: uuid.UUID, path: Path
) -> Optional[ffms2.VideoSource]:
    """Create video source.

    :param log_api: logging API
    :param uid: uid of the stream (for logging)
    :param path: path to the video file
    :return: input path and resulting video source
    """
    log_api.info(f"video {uid} started loading ({path})")

    if not path.exists():
        log_api.error(f"error loading video {uid} (file {path} not found)")
        return None

    try:
        source = ffms2.VideoSource(str(path))
    except ffms2.Error as ex:
        log_api.error(f"error loading video {uid} ({ex})")
        return None
    else:
        log_api.info(f"video {uid} finished loading")
        return source


class VideoStream(BaseStream, QObject):
    """The video API."""

    errored = cast(ClassVar[pyqtBoundSignal], pyqtSignal())
    changed = cast(ClassVar[pyqtBoundSignal], pyqtSignal())
    loaded = cast(ClassVar[pyqtBoundSignal], pyqtSignal())

    def __init__(
        self,
        threading_api: ThreadingApi,
        log_api: LogApi,
        subs_api: SubtitlesApi,
        path: Path,
    ) -> None:
        """Initialize self.

        :param threading_api: threading API
        :param log_api: logging API
        :param subs_api: subtitles API
        :param path: path to the video file to load
        """
        super().__init__()
        self._threading_api = threading_api
        self._log_api = log_api
        self._subs_api = subs_api

        self.uid = uuid.uuid4()

        self._path = path
        self._timecodes: Optional[list[int]] = None
        self._keyframes: Optional[list[int]] = None
        self._frame_rate: Optional[Fraction] = None
        self._aspect_ratio: Optional[Fraction] = None
        self._width: Optional[int] = None
        self._height: Optional[int] = None

        self._ass_renderer = AssRenderer()
        self._source: Union[None, ffms2.VideoSource] = None

        self._last_output_fmt: Any = None

        self._log_api.info(f"video: loading {path}")
        self._threading_api.schedule_task(
            lambda: _load_video_source(self._log_api, self.uid, self._path),
            self._got_source,
        )

    @property
    def path(self) -> Path:
        """Return video source path.

        :return: path
        """
        return self._path

    @property
    def is_ready(self) -> bool:
        """Return whether the video is loaded.

        :return: whether the video is loaded
        """
        return self._source is not None

    def screenshot(
        self,
        pts: int,
        path: Path,
        include_subtitles: bool,
        width: Optional[int],
        height: Optional[int],
    ) -> None:
        """Save a screenshot into specified destination.

        :param pts: pts to make screenshot of
        :param path: path to save the screenshot to
        :param include_subtitles: whether to 'burn in' the subtitles
        :param width: optional width to render to
        :param height: optional height to render to
        """
        if width and height:
            grab_width = width
            grab_height = height
        elif height:
            grab_width = int(self.width * height / self.height)
            grab_height = height
        elif width:
            grab_height = int(self.height * width / self.width)
            grab_width = width
        else:
            grab_width = self.width
            grab_height = self.height

        if grab_width <= 0 or grab_height <= 0:
            raise ValueError("cannot take a screenshot at negative resolution")

        pts = self.align_pts_to_prev_frame(pts)
        idx = self.timecodes.index(pts)
        frame = self.get_frame(idx, grab_width, grab_height)
        if not frame.flags.c_contiguous:
            frame = frame.copy(order="C")
        image = PIL.Image.frombytes("RGB", (grab_width, grab_height), frame)

        if include_subtitles:
            self._ass_renderer.set_source(
                self._subs_api.ass_file,
                (grab_width, grab_height),
            )
            subs_image = self._ass_renderer.render(
                time=pts, aspect_ratio=self.aspect_ratio
            )
            image = PIL.Image.composite(subs_image, image, subs_image)

        image.save(str(path))

    def align_pts_to_near_frame(self, pts: int) -> int:
        """Align PTS to a frame closest to given PTS.

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
        """Align PTS to a frame immediately before given PTS.

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
        """Align PTS to a frame immediately after given PTS.

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

    def frame_idx_from_pts(
        self, pts: Union[float, int, np.ndarray]
    ) -> Union[int, np.ndarray]:
        """Get index of a frame that contains given PTS.

        :param pts: PTS to search for
        :return: frame index, -1 if not found
        """
        ret = np.searchsorted(self.timecodes, pts, "right").astype(np.int32)
        ret = np.clip(ret - 1, a_min=0 if self.timecodes else -1, a_max=None)
        return ret

    @property
    def frame_rate(self) -> Fraction:
        """Return the frame rate.

        Raises an exception if the stream is not fully loaded yet.

        :return: video frame rate
        """
        if self._frame_rate is None:
            raise VideoStreamUnavailable
        return self._frame_rate

    @property
    def width(self) -> int:
        """Return horizontal video resolution.

        Raises an exception if the stream is not fully loaded yet.

        :return: video width in pixels
        """
        if self._width is None:
            raise VideoStreamUnavailable
        return self._width

    @property
    def height(self) -> int:
        """Return vertical video resolution.

        Raises an exception if the stream is not fully loaded yet.

        :return: video height in pixels
        """
        if self._height is None:
            raise VideoStreamUnavailable
        return self._height

    @property
    def aspect_ratio(self) -> Fraction:
        """Return the frame aspect ratio.

        Raises an exception if the stream is not fully loaded yet.

        :return: video frame aspect ratio
        """
        if self._aspect_ratio is None:
            raise VideoStreamUnavailable
        return self._aspect_ratio

    @property
    def timecodes(self) -> list[int]:
        """Return video frames' PTS.

        Raises an exception if the stream is not fully loaded yet.

        :return: video frames' PTS
        """
        if self._timecodes is None:
            raise VideoStreamUnavailable
        return self._timecodes

    @property
    def keyframes(self) -> list[int]:
        """Return video keyframes' indexes.

        Raises an exception if the stream is not fully loaded yet.

        :return: video keyframes' indexes
        """
        if self._keyframes is None:
            raise VideoStreamUnavailable
        return self._keyframes

    @property
    def min_pts(self) -> int:
        """Return minimum video time in milliseconds.

        Raises an exception if the stream is not fully loaded yet.

        :return: minimum PTS
        """
        if not self.timecodes:
            return 0
        return self.timecodes[0]

    @property
    def max_pts(self) -> int:
        """Return maximum video time in milliseconds.

        Raises an exception if the stream is not fully loaded yet.

        :return: maximum PTS
        """
        if not self.timecodes:
            return 0
        return self.timecodes[-1]

    def get_frame(self, frame_idx: int, width: int, height: int) -> np.ndarray:
        """Get raw video data from the currently loaded video source.

        :param frame_idx: frame number
        :param width: output image width
        :param height: output image height
        :return: numpy image
        """
        with _SAMPLER_LOCK:
            if frame_idx < 0 or frame_idx >= len(self.timecodes):
                raise ValueError("bad frame")
            assert self._source

            new_output_fmt = (_PIX_FMT, width, height, ffms2.FFMS_RESIZER_AREA)
            if self._last_output_fmt != new_output_fmt:
                self._source.set_output_format(*new_output_fmt)
                self._last_output_fmt = new_output_fmt

            frame = self._source.get_frame(frame_idx)
            return (
                frame.planes[0]
                .reshape((height, frame.Linesize[0]))[:, 0 : width * 3]
                .reshape(height, width, 3)
            )

    async def async_get_frame(
        self, frame_idx: int, width: int, height: int
    ) -> np.ndarray:
        """Get raw video data from the currently loaded video source
        asynchronously.

        :param frame_idx: frame number
        :param width: output image width
        :param height: output image height
        :return: numpy image
        """
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def _worker() -> None:
            result = self.get_frame(frame_idx, width, height)
            loop.call_soon_threadsafe(future.set_result, result)

        asyncio.get_event_loop().run_in_executor(None, _worker)
        return await future

    def _got_source(self, source: ffms2.VideoSource) -> None:
        with _SAMPLER_LOCK:
            self._source = source

            if source is None:
                self.errored.emit()
                return

            self._timecodes = sorted(
                [int(round(pts)) for pts in source.track.timecodes]
            )
            self._keyframes = sorted(source.track.keyframes[:])

            self._frame_rate = Fraction(
                self._source.properties.FPSNumerator,
                self._source.properties.FPSDenominator,
            )

            self._aspect_ratio = (
                Fraction(
                    self._source.properties.SARNum,
                    self._source.properties.SARDen,
                )
                if (
                    self._source.properties.SARNum
                    and self._source.properties.SARDen
                )
                else Fraction(1, 1)
            )

            frame = source.get_frame(0)
            self._width = frame.EncodedWidth
            self._height = int(frame.EncodedHeight / self.aspect_ratio)
            self.loaded.emit()
