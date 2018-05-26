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

import bisect
import typing as T

import numpy as np
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.api.media.audio
import bubblesub.worker
from bubblesub.api.media.state import MediaState
from bubblesub.ui.audio.base import BaseAudioWidget
from bubblesub.ui.audio.base import SLIDER_SIZE

NOT_CACHED = object()
CACHING: np.array = np.array([])
BAND_Y_RESOLUTION = 30


class VideoBandWorker(bubblesub.worker.Worker):
    def __init__(self, api: bubblesub.api.Api) -> None:
        super().__init__()
        self._api = api

    def _do_work(self, task: T.Any) -> T.Any:
        frame_idx, width, height = task
        out = self._api.media.video.get_frame(frame_idx, width, height).copy()
        return (frame_idx, width, height, out)


class VideoPreview(BaseAudioWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(api, parent)
        self.setMinimumHeight(SLIDER_SIZE * 3)
        self._worker = VideoBandWorker(api)
        self._worker.task_finished.connect(self._on_video_update)
        self._worker.start()

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Maximum
        )

        self._cache: T.Dict[int, np.array] = {}
        self._need_repaint = False
        self._pixels: np.array = np.zeros([0, 0, 3], dtype=np.uint8)

        timer = QtCore.QTimer(self)
        timer.setInterval(api.opt.general.audio.spectrogram_sync_interval)
        timer.timeout.connect(self._repaint_if_needed)
        timer.start()

        api.media.state_changed.connect(self._on_media_state_change)
        api.media.audio.view_changed.connect(self._on_audio_view_change)
        api.media.video.parsed.connect(self._on_audio_view_change)

    def resizeEvent(self, _event: QtGui.QResizeEvent) -> None:
        self._pixels = np.zeros(
            [BAND_Y_RESOLUTION, self.width(), 3],
            dtype=np.uint8
        )

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()

        painter.begin(self)
        self._draw_video_band(painter)
        self._draw_frame(painter)
        painter.end()

        self._need_repaint = False

    def _repaint_if_needed(self) -> None:
        if self._need_repaint:
            self.update()

    def _on_audio_view_change(self) -> None:
        self._need_repaint = True

        self._cache = {
            key: value
            for key, value in self._cache.items()
            if value is not CACHING
        }
        self._worker.clear_tasks()

        for x in reversed(range(self.width() * 2)):
            frame_idx = self._frame_idx_from_x(x)
            if frame_idx not in self._cache:
                self._worker.schedule_task((frame_idx, 1, BAND_Y_RESOLUTION))
                self._cache[frame_idx] = CACHING

    def _on_media_state_change(self, _state: MediaState) -> None:
        self._cache.clear()
        self._worker.clear_tasks()
        self.update()

    def _on_video_update(
            self,
            result: T.Tuple[int, int, int, np.array]
    ) -> None:
        frame, _width, height, column = result
        self._cache[frame] = column.reshape(height, 3)
        self._need_repaint = True

    def _draw_frame(self, painter: QtGui.QPainter) -> None:
        painter.setPen(
            QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine)
        )
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(
            0,
            0,
            painter.viewport().width() - 1,
            painter.viewport().height() - 1
        )

    def _draw_video_band(self, painter: QtGui.QPainter) -> None:
        pixels = self._pixels.transpose(1, 0, 2)
        prev_column = np.zeros([pixels.shape[1], 3], dtype=np.uint8)
        for x in range(pixels.shape[0]):
            frame_idx = self._frame_idx_from_x(x)
            column = self._cache.get(frame_idx, NOT_CACHED)
            if column is NOT_CACHED or column is CACHING:
                column = prev_column
            else:
                prev_column = column
            pixels[x] = column

        image = QtGui.QImage(
            self._pixels.data,
            self._pixels.shape[1],
            self._pixels.shape[0],
            self._pixels.strides[0],
            QtGui.QImage.Format_RGB888
        )
        painter.save()
        painter.scale(1, painter.viewport().height() / (BAND_Y_RESOLUTION - 1))
        painter.drawPixmap(0, 0, QtGui.QPixmap.fromImage(image))
        painter.restore()

    def _frame_idx_from_x(self, x: int) -> int:
        scale = self._audio.view_size / self.width()
        pts = int(x * scale + self._audio.view_start)
        return max(
            0,
            bisect.bisect_left(self._api.media.video.timecodes, pts) - 1
        )
