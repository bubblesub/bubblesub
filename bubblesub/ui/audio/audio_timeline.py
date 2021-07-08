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
from bubblesub.ui.audio.base import SLIDER_SIZE, BaseLocalAudioWidget, DragMode
from bubblesub.ui.themes import ThemeManager


class AudioTimeline(BaseLocalAudioWidget):
    def __init__(
        self, api: Api, theme_mgr: ThemeManager, parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(api, parent)
        self._theme_mgr = theme_mgr
        self.setFixedHeight(SLIDER_SIZE)

        api.audio.stream_loaded.connect(self.repaint_if_needed)
        api.audio.stream_unloaded.connect(self.repaint_if_needed)
        api.audio.current_stream_switched.connect(self.repaint_if_needed)

        api.audio.view.view_changed.connect(self.repaint_if_needed)
        api.playback.current_pts_changed.connect(
            self.repaint, QtCore.Qt.DirectConnection
        )

    def _get_paint_cache_key(self) -> int:
        with self._api.video.stream_lock:
            return hash(
                (
                    # keyframes
                    (
                        self._api.video.current_stream.uid
                        if self._api.video.current_stream
                        else None
                    ),
                    # audio view
                    self._api.audio.view.view_start,
                    self._api.audio.view.view_end,
                    # video position
                    self._api.playback.current_pts,
                )
            )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_scale(painter)
        self._draw_frame(painter, bottom_line=False)
        self._draw_keyframes(painter)
        self._draw_video_pos(painter)
        painter.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.begin_drag_mode(DragMode.VIDEO_POSITION, event)
        elif event.button() == QtCore.Qt.MiddleButton:
            self.begin_drag_mode(DragMode.VIDEO_POSITION, event)
            self.end_drag_mode()

    def _draw_scale(self, painter: QtGui.QPainter) -> None:
        h = painter.viewport().height()
        one_second = 1000
        one_minute = 60 * one_second

        start_pts = int(self._view.view_start // one_minute) * one_minute
        end_pts = (
            int(self._view.view_end + one_minute) // one_minute
        ) * one_minute

        painter.setPen(
            QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine)
        )
        painter.setFont(QtGui.QFont(self.font().family(), 8))
        text_height = painter.fontMetrics().capHeight()

        for pts in range(start_pts, end_pts, one_second):
            x = round(self.pts_to_x(pts))
            if x < 0 or x >= self.width():
                continue

            if pts % one_minute == 0:
                gap = h - 1
            else:
                gap = 4

            painter.drawLine(x, 0, x, gap)
            if pts % one_minute == 0:
                text = "{:02}:{:02}".format(pts // one_minute, 0)
            elif pts % (10 * one_second) == 0:
                long_text = "{:02}:{:02}".format(
                    pts // one_minute, (pts % one_minute) // one_second
                )
                long_text_width = painter.fontMetrics().width(long_text)
                next_label_x = round(self.pts_to_x(pts + 10 * one_second))
                if long_text_width < next_label_x - x:
                    text = long_text
                else:
                    text = "{:02}".format((pts % one_minute) // one_second)
            else:
                continue
            painter.drawText(x + 2, text_height + (h - text_height) / 2, text)

    def _draw_keyframes(self, painter: QtGui.QPainter) -> None:
        h = painter.viewport().height()
        color = self._theme_mgr.get_color("spectrogram/keyframe")
        painter.setPen(QtGui.QPen(color, 1, QtCore.Qt.SolidLine))
        if self._api.video.current_stream:
            for keyframe in self._api.video.current_stream.keyframes:
                timecode = self._api.video.current_stream.timecodes[keyframe]
                x = round(self.pts_to_x(timecode))
                painter.drawLine(x, 0, x, h)

    def _draw_video_pos(self, painter: QtGui.QPainter) -> None:
        if not self._api.playback.current_pts:
            return
        x = round(self.pts_to_x(self._api.playback.current_pts))
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._theme_mgr.get_color("spectrogram/video-marker"))

        width = 7
        polygon = QtGui.QPolygonF()
        for x, y in [
            (x - width // 2, 0),
            (x + width // 2, 0),
            (x + width // 2, painter.viewport().height()),
            (x - width // 2, painter.viewport().height()),
        ]:
            polygon.append(QtCore.QPoint(x, y))

        painter.drawPolygon(polygon)
