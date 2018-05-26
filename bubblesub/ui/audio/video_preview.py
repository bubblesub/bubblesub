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


class VideoBandWorker(bubblesub.worker.Worker):
    def __init__(self, api: bubblesub.api.Api) -> None:
        super().__init__()
        self._api = api

    def _do_work(self, task: T.Any) -> T.Any:
        frame_idx, width, height = task
        out = self._api.media.video.get_frame(frame_idx, width, height)
        return (frame_idx, width, height, out.copy())


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

        timer = QtCore.QTimer(self)
        timer.setInterval(api.opt.general.audio.spectrogram_sync_interval)
        timer.timeout.connect(self._repaint_if_needed)
        timer.start()

        api.media.current_pts_changed.connect(
            self._on_video_current_pts_change
        )
        api.media.state_changed.connect(self._on_media_state_change)
        api.media.audio.view_changed.connect(self._on_audio_view_change)

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()

        painter.begin(self)
        painter.save()
        self._draw_video_band(painter)
        self._draw_frame(painter)
        painter.restore()
        painter.end()

        self._need_repaint = False

    def _repaint_if_needed(self) -> None:
        if self._need_repaint:
            self.update()

    def _on_audio_view_change(self) -> None:
        self._cache = {
            key: value
            for key, value in self._cache.items()
            if value is not CACHING
        }
        self._worker.clear_tasks()

    def _on_media_state_change(self, _state: MediaState) -> None:
        self._cache.clear()
        self._worker.clear_tasks()
        self.update()

    def _on_video_current_pts_change(self) -> None:
        self._need_repaint = True

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
        width = painter.viewport().width()
        height = 30

        pixels = np.zeros([width, height, 3], dtype=np.uint8)

        for x in reversed(range(width)):
            pts = self._pts_from_x(x)
            frame_idx = self._frame_from_pts(pts)
            column = self._cache.get(frame_idx, NOT_CACHED)
            if column is NOT_CACHED:
                self._worker.schedule_task((frame_idx, 1, height))
                self._cache[frame_idx] = CACHING
                continue
            if column is CACHING:
                continue
            pixels[x] = column

        pixels = pixels.transpose((1, 0, 2)).copy()

        image = QtGui.QImage(
            pixels.data,
            width,
            height,
            pixels.strides[0],
            QtGui.QImage.Format_RGB888
        )
        painter.save()
        painter.scale(1, painter.viewport().height() / (height - 1))
        painter.drawPixmap(0, 0, QtGui.QPixmap.fromImage(image))
        painter.restore()

    def _frame_from_pts(self, pts: int) -> int:
        return max(
            0,
            bisect.bisect_left(self._api.media.video.timecodes, pts) - 1
        )

    def _pts_from_x(self, x: float) -> int:
        scale = self._audio.view_size / self.width()
        return int(x * scale + self._audio.view_start)
