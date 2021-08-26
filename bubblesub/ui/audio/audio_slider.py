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

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QMouseEvent, QPainter, QPaintEvent, QPen
from PyQt5.QtWidgets import QWidget

from bubblesub.api import Api
from bubblesub.ui.audio.base import (
    SLIDER_SIZE,
    BaseGlobalAudioWidget,
    DragMode,
)
from bubblesub.ui.themes import ThemeManager


class AudioSlider(BaseGlobalAudioWidget):
    def __init__(
        self, api: Api, theme_mgr: ThemeManager, parent: QWidget
    ) -> None:
        super().__init__(api, parent)
        self._theme_mgr = theme_mgr

        self.setFixedHeight(SLIDER_SIZE)

        api.audio.view.selection_changed.connect(self.repaint_if_needed)
        api.audio.view.view_changed.connect(self.repaint_if_needed)
        api.playback.current_pts_changed.connect(
            self.repaint, Qt.ConnectionType.DirectConnection
        )
        api.subs.loaded.connect(self._on_subs_load)

    def _on_subs_load(self) -> None:
        self._api.subs.events.changed.subscribe(
            lambda _event: self.repaint_if_needed()
        )

    def _get_paint_cache_key(self) -> int:
        with self._api.video.stream_lock:
            return hash(
                (
                    # subtitle rectangles
                    tuple(
                        (event.start, event.end)
                        for event in self._api.subs.events
                    ),
                    # audio view
                    self._api.audio.view.view_start,
                    self._api.audio.view.view_end,
                    # video position
                    self._api.playback.current_pts,
                )
            )

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)
        self._draw_subtitle_rects(painter)
        self._draw_slider(painter)
        self._draw_video_pos(painter)
        self._draw_frame(painter, bottom_line=True)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin_drag_mode(DragMode.AUDIO_VIEW, event)
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.begin_drag_mode(DragMode.AUDIO_VIEW, event)
            self.end_drag_mode()

    def _draw_video_pos(self, painter: QPainter) -> None:
        if not self._api.playback.current_pts:
            return
        x = round(self.pts_to_x(self._api.playback.current_pts))
        painter.setPen(
            QPen(
                self._theme_mgr.get_color("spectrogram/video-marker"),
                1,
                Qt.PenStyle.SolidLine,
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(x, 0, x, self.height())

    def _draw_subtitle_rects(self, painter: QPainter) -> None:
        h = self.height()
        painter.setPen(Qt.PenStyle.NoPen)
        color = self.palette().highlight().color()
        color.setAlpha(40)
        painter.setBrush(QBrush(color))
        for line in self._api.subs.events:
            x1 = round(self.pts_to_x(line.start))
            x2 = round(self.pts_to_x(line.end))
            painter.drawRect(x1, 0, x2 - x1, h - 1)

    def _draw_slider(self, painter: QPainter) -> None:
        h = self.height()
        band_size = h // 4
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.palette().highlight()))
        x1 = round(self.pts_to_x(self._view.view_start))
        x2 = round(self.pts_to_x(self._view.view_end))
        painter.drawRect(x1, 0, x2 - x1, band_size)
        painter.drawRect(x1, h - band_size, x2 - x1, band_size)
