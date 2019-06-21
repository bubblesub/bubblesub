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

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.log import LogApi
from bubblesub.api.threading import QueueWorker
from bubblesub.api.video import VideoApi, VideoState
from bubblesub.cache import load_cache, save_cache
from bubblesub.ui.audio.base import SLIDER_SIZE, BaseLocalAudioWidget
from bubblesub.util import sanitize_file_name

_CACHE_LOCK = threading.Lock()
_NOT_CACHED = object()
_BAND_Y_RESOLUTION = 30


class VideoBandWorkerSignals(QtCore.QObject):
    cache_updated = QtCore.pyqtSignal()


class VideoBandWorker(QueueWorker):
    def __init__(self, log_api: LogApi, video_api: VideoApi) -> None:
        super().__init__(log_api)
        self.signals = VideoBandWorkerSignals()
        self._video_api = video_api

        self._anything_to_save = False
        self._cache_name: T.Optional[str] = None
        self.cache: T.Dict[int, np.array] = {}

        video_api.state_changed.connect(self._on_video_state_change)

    def _process_task(self, task: T.Any) -> None:
        frame_idx = T.cast(int, task)
        frame = self._video_api.get_frame(frame_idx, 1, _BAND_Y_RESOLUTION)
        if frame is None:
            return
        frame = frame.reshape(_BAND_Y_RESOLUTION, 3)
        with _CACHE_LOCK:
            self.cache[frame_idx] = frame.copy()
        self._anything_to_save = True
        self.signals.cache_updated.emit()

    def _queue_cleared(self) -> None:
        with _CACHE_LOCK:
            self._save_to_cache()

    def _on_video_state_change(self, state: VideoState) -> None:
        if state == VideoState.NotLoaded:
            with _CACHE_LOCK:
                if self._anything_to_save:
                    self._save_to_cache()
                self.clear_tasks()
                self._cache_name = None
                self.cache = {}
            self.signals.cache_updated.emit()

        elif state == VideoState.Loading:
            with _CACHE_LOCK:
                assert self._video_api.path
                self._cache_name = (
                    sanitize_file_name(self._video_api.path) + "-video-band"
                )
                self.clear_tasks()
                self._anything_to_save = False
                self.cache = self._load_from_cache()
            self.signals.cache_updated.emit()

        elif state == VideoState.Loaded:
            with _CACHE_LOCK:
                for frame_idx in range(len(self._video_api.timecodes)):
                    if frame_idx not in self.cache:
                        self._queue.put(frame_idx)

    def _load_from_cache(self) -> T.Dict[int, np.array]:
        if self._cache_name is None:
            return {}
        cache = load_cache(self._cache_name) or {}
        cache = {
            key: value
            for key, value in cache.items()
            if np.count_nonzero(value)
        }
        return cache

    def _save_to_cache(self) -> None:
        if self._cache_name is not None:
            save_cache(self._cache_name, self.cache)


class VideoPreview(BaseLocalAudioWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(api, parent)
        self.setMinimumHeight(SLIDER_SIZE * 3)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum
        )

        self._worker = VideoBandWorker(api.log, api.video)
        self._worker.signals.cache_updated.connect(self._on_video_band_update)
        self._api.threading.schedule_runnable(self._worker)

        self._need_repaint = False
        self._pixels: np.array = np.zeros([0, 0, 3], dtype=np.uint8)

        timer = QtCore.QTimer(self)
        timer.setInterval(api.cfg.opt["audio"]["spectrogram_sync_interval"])
        timer.timeout.connect(self._repaint_if_needed)
        timer.start()

        api.audio.view.view_changed.connect(self._on_audio_view_change)
        api.video.state_changed.connect(self.update)

    def shutdown(self) -> None:
        self._worker.stop()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._pixels = np.zeros(
            [_BAND_Y_RESOLUTION, self.width(), 3], dtype=np.uint8
        )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()

        painter.begin(self)
        self._draw_video_band(painter)
        self._draw_frame(painter, bottom_line=False)
        painter.end()

        self._need_repaint = False

    def _repaint_if_needed(self) -> None:
        if self._need_repaint:
            self.update()

    def _on_audio_view_change(self) -> None:
        self._need_repaint = True

    def _on_video_band_update(self) -> None:
        self._need_repaint = True

    def _draw_video_band(self, painter: QtGui.QPainter) -> None:
        pixels = self._pixels.transpose(1, 0, 2)
        prev_column = np.zeros([pixels.shape[1], 3], dtype=np.uint8)
        for x in range(pixels.shape[0]):
            frame_idx = self.frame_idx_from_x(x)
            column = self._worker.cache.get(frame_idx, _NOT_CACHED)
            if column is _NOT_CACHED:
                column = prev_column
            else:
                prev_column = column
            pixels[x] = column

        image = QtGui.QImage(
            self._pixels.data,
            self._pixels.shape[1],
            self._pixels.shape[0],
            self._pixels.strides[0],
            QtGui.QImage.Format_RGB888,
        )
        painter.save()
        painter.scale(
            1, painter.viewport().height() / (_BAND_Y_RESOLUTION - 1)
        )
        painter.drawPixmap(0, 0, QtGui.QPixmap.fromImage(image))
        painter.restore()
