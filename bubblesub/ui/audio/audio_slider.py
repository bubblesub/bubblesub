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

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.ui.audio.base import (
    SLIDER_SIZE,
    BaseGlobalAudioWidget,
    DragMode,
)


class AudioSlider(BaseGlobalAudioWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(api, parent)
        self.setFixedHeight(SLIDER_SIZE)

        api.audio.view.selection_changed.connect(self.repaint_if_needed)
        api.audio.view.view_changed.connect(self.repaint_if_needed)
        api.playback.current_pts_changed.connect(
            self.repaint, QtCore.Qt.DirectConnection
        )
        api.subs.events.item_changed.connect(self.repaint_if_needed)
        api.subs.events.items_inserted.connect(self.repaint_if_needed)
        api.subs.events.items_moved.connect(self.repaint_if_needed)
        api.subs.events.items_removed.connect(self.repaint_if_needed)

    def _get_paint_cache_key(self) -> int:
        return hash(
            tuple(
                # subtitle rectangles
                [(event.start, event.end) for event in self._api.subs.events]
                + [
                    # audio view
                    self._api.audio.view.view_start,
                    self._api.audio.view.view_end,
                    # video position
                    self._api.playback.current_pts,
                ]
            )
        )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_subtitle_rects(painter)
        self._draw_slider(painter)
        self._draw_video_pos(painter)
        self._draw_frame(painter, bottom_line=True)
        painter.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.begin_drag_mode(DragMode.AudioView, event)
        elif event.button() == QtCore.Qt.MiddleButton:
            self.begin_drag_mode(DragMode.AudioView, event)
            self.end_drag_mode()

    def _draw_video_pos(self, painter: QtGui.QPainter) -> None:
        if not self._api.playback.current_pts:
            return
        x = round(self.pts_to_x(self._api.playback.current_pts))
        painter.setPen(
            QtGui.QPen(
                self._api.gui.get_color("spectrogram/video-marker"),
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
            x1 = round(self.pts_to_x(line.start))
            x2 = round(self.pts_to_x(line.end))
            painter.drawRect(x1, 0, x2 - x1, h - 1)

    def _draw_slider(self, painter: QtGui.QPainter) -> None:
        h = self.height()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(self.palette().highlight()))
        x1 = round(self.pts_to_x(self._view.view_start))
        x2 = round(self.pts_to_x(self._view.view_end))
        painter.drawRect(x1, 0, x2 - x1, h / 4)
        painter.drawRect(x1, h - 1 - h / 4, x2 - x1, h / 4)
