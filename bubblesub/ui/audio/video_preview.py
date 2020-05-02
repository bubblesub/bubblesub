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

import threading
import typing as T
import uuid

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.log import LogApi
from bubblesub.api.threading import QueueWorker
from bubblesub.api.video import VideoApi
from bubblesub.api.video_stream import VideoStream
from bubblesub.cache import load_cache, save_cache
from bubblesub.ui.audio.base import BaseLocalAudioWidget
from bubblesub.util import chunks, sanitize_file_name

_CACHE_LOCK = threading.Lock()
BAND_RESOLUTION = 30
CHUNK_SIZE = 500
VIDEO_BAND_SIZE = 10


class VideoBandWorkerSignals(QtCore.QObject):
    cache_updated = QtCore.pyqtSignal()


class VideoBandWorker(QueueWorker):
    def __init__(self, log_api: LogApi, video_api: VideoApi) -> None:
        super().__init__(log_api)
        self.signals = VideoBandWorkerSignals()
        self._video_api = video_api

        self.cache: T.Dict[uuid.UUID, np.array] = {}

        video_api.stream_loaded.connect(self._on_video_stream_load)

    def _process_task(self, task: T.Any) -> None:
        stream, frame_indexes = task
        anything_changed = False
        for frame_idx in frame_indexes:
            frame = stream.get_frame(frame_idx, 1, BAND_RESOLUTION)
            if frame is None:
                continue
            frame = frame.reshape(BAND_RESOLUTION, 3)
            with _CACHE_LOCK:
                self.cache[stream.uid][frame_idx] = frame
            anything_changed = True
        if anything_changed:
            self.signals.cache_updated.emit()
            cache_name = self._get_cache_name(stream)
            save_cache(cache_name, self.cache[stream.uid])

    def _get_cache_name(self, stream: VideoStream) -> str:
        try:
            size = stream.path.stat().st_size
        except FileNotFoundError:
            size = 0
        return sanitize_file_name(stream.path) + f"-{size}-video-band"

    def _on_video_stream_unload(self, stream: VideoStream) -> None:
        with _CACHE_LOCK:
            # TODO: this also clears queue for unrelated streams!
            self.clear_tasks()
            cache_name = self._get_cache_name(stream)
            save_cache(cache_name, self.cache[stream.uid])
            del self.cache[stream.uid]

    def _on_video_stream_load(self, stream: VideoStream) -> None:
        with _CACHE_LOCK:
            cache_name = self._get_cache_name(stream)
            cache = load_cache(cache_name)
            if cache is None:
                cache = np.zeros(
                    [len(stream.timecodes), BAND_RESOLUTION, 3], dtype=np.uint8
                )
            self.cache[stream.uid] = cache

            not_cached_frames = [
                frame_idx
                for frame_idx in range(cache.shape[0])
                if not np.count_nonzero(cache[frame_idx])
            ]
            for chunk in chunks(not_cached_frames, CHUNK_SIZE):
                self._queue.put((stream, chunk))


class VideoPreview(BaseLocalAudioWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(api, parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred
        )

        self._pixels: np.array = np.zeros([0, 0, 3], dtype=np.uint8)

        self._worker = VideoBandWorker(api.log, api.video)
        self._worker.signals.cache_updated.connect(self.repaint)
        self._api.threading.schedule_runnable(self._worker)

        api.video.stream_loaded.connect(self.repaint_if_needed)
        api.video.stream_unloaded.connect(self.repaint_if_needed)
        api.video.current_stream_switched.connect(self.repaint_if_needed)
        api.audio.view.view_changed.connect(self.repaint_if_needed)
        api.gui.terminated.connect(self.shutdown)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(0, VIDEO_BAND_SIZE)

    def _get_paint_cache_key(self) -> int:
        with self._api.video.stream_lock:
            return hash(
                (
                    # frame bitmaps
                    (
                        self._api.video.current_stream.uid
                        if self._api.video.current_stream
                        else None
                    ),
                    # audio view
                    self._api.audio.view.view_start,
                    self._api.audio.view.view_end,
                )
            )

    def shutdown(self) -> None:
        self._worker.stop()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._pixels = np.zeros(
            [BAND_RESOLUTION, self.width(), 3], dtype=np.uint8
        )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()

        painter.begin(self)
        self._draw_video_band(painter)
        self._draw_frame(painter, bottom_line=False)
        painter.end()

    def _draw_video_band(self, painter: QtGui.QPainter) -> None:
        current_stream = self._api.video.current_stream
        if not current_stream or not current_stream.timecodes:
            return

        pixels = self._pixels.transpose(1, 0, 2)

        min_pts = self.pts_from_x(0)
        max_pts = self.pts_from_x(self.width() - 1)

        pts_range = np.linspace(min_pts, max_pts, self.width())
        frame_idx_range = self._api.video.current_stream.frame_idx_from_pts(
            pts_range
        )

        cache = self._worker.cache.get(current_stream.uid)
        if cache is not None:
            for x, frame_idx in enumerate(frame_idx_range):
                pixels[x] = cache[frame_idx]

        image = QtGui.QImage(
            self._pixels.data,
            self._pixels.shape[1],
            self._pixels.shape[0],
            self._pixels.strides[0],
            QtGui.QImage.Format_RGB888,
        )
        painter.save()
        painter.scale(1, painter.viewport().height() / (BAND_RESOLUTION - 1))
        painter.drawPixmap(0, 0, QtGui.QPixmap.fromImage(image))
        painter.restore()
