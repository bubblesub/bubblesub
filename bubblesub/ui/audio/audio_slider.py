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

import typing as T

from PyQt5 import QtCore, QtGui, QtWidgets

import bubblesub.api
import bubblesub.api.media.audio
from bubblesub.ui.audio.base import SLIDER_SIZE, BaseAudioWidget
from bubblesub.ui.util import get_color


class AudioSlider(BaseAudioWidget):
    def __init__(
        self, api: bubblesub.api.Api, parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(api, parent)
        self.setFixedHeight(SLIDER_SIZE)
        api.media.current_pts_changed.connect(
            self._on_video_current_pts_change
        )

    def _on_video_current_pts_change(self) -> None:
        self.update()

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_subtitle_rects(painter)
        self._draw_slider(painter)
        self._draw_video_pos(painter)
        self._draw_frame(painter)
        painter.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.setCursor(QtCore.Qt.SizeHorCursor)
        self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, _event: QtGui.QMouseEvent) -> None:
        self.setCursor(QtCore.Qt.ArrowCursor)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        old_center = self._audio.view_start + self._audio.view_size / 2
        new_center = self._pts_from_x(event.x())
        distance = new_center - old_center
        self._audio.move_view(int(distance))

    def _draw_video_pos(self, painter: QtGui.QPainter) -> None:
        if not self._api.media.current_pts:
            return
        x = self._pts_to_x(self._api.media.current_pts)
        painter.setPen(
            QtGui.QPen(
                get_color(self._api, "spectrogram/video-marker"),
                1,
                QtCore.Qt.SolidLine,
            )
        )
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawLine(x, 0, x, self.height())

    def _draw_subtitle_rects(self, painter: QtGui.QPainter) -> None:
        h = self.height()
        painter.setPen(QtCore.Qt.NoPen)
        color = self.palette().highlight().color()
        color.setAlpha(40)
        painter.setBrush(QtGui.QBrush(color))
        for line in self._api.subs.events:
            x1 = self._pts_to_x(line.start)
            x2 = self._pts_to_x(line.end)
            painter.drawRect(x1, 0, x2 - x1, h - 1)

    def _draw_slider(self, painter: QtGui.QPainter) -> None:
        h = self.height()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(self.palette().highlight()))
        x1 = self._pts_to_x(self._audio.view_start)
        x2 = self._pts_to_x(self._audio.view_end)
        painter.drawRect(x1, 0, x2 - x1, h / 4)
        painter.drawRect(x1, h - 1 - h / 4, x2 - x1, h / 4)

    def _draw_frame(self, painter: QtGui.QPainter) -> None:
        w, h = self.width(), self.height()
        painter.setPen(
            QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine)
        )
        painter.drawLine(0, 0, 0, h - 1)
        painter.drawLine(w - 1, 0, w - 1, h - 1)
        painter.drawLine(0, h - 1, w - 1, h - 1)

    def _pts_to_x(self, pts: int) -> float:
        scale = T.cast(int, self.width()) / max(1, self._audio.size)
        return (pts - self._audio.min) * scale

    def _pts_from_x(self, x: float) -> int:
        scale = self._audio.size / self.width()
        return int(x * scale + self._audio.min)
