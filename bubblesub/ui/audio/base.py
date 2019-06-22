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

import enum
import typing as T
from dataclasses import dataclass

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.audio_view import AudioViewApi
from bubblesub.fmt.ass.event import AssEvent

SLIDER_SIZE = 20


class DragMode(enum.Enum):
    SelectionStart = 1
    SelectionEnd = 2
    VideoPosition = 3
    AudioView = 4
    SubtitleStart = 5
    SubtitleEnd = 6
    NewSubtitleStart = 7
    NewSubtitleEnd = 8


@dataclass
class DragData:
    mode: DragMode
    selected_events: T.List[AssEvent]


def _create_new_subtitle(api: Api, pts: int, before: bool) -> None:
    pts = api.video.align_pts_to_near_frame(pts)

    if before:
        if not api.subs.selected_indexes:
            return
        end = api.subs.selected_events[0].start
        idx = api.subs.selected_indexes[0]
        start = pts
    else:
        if api.subs.selected_indexes:
            start = api.subs.selected_events[-1].end
            idx = api.subs.selected_indexes[-1] + 1
        else:
            start = 0
            idx = 0
        end = pts

    api.subs.events.insert(
        idx, AssEvent(start=start, end=end, style=api.subs.default_style_name)
    )
    api.subs.selected_indexes = [idx]


class BaseAudioWidget(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self._api = api
        self._drag_data: T.Optional[DragData] = None
        self._last_paint_cache_key = 0

    def repaint(self) -> None:
        self._last_paint_cache_key = self._get_paint_cache_key()
        self.update()

    def repaint_if_needed(self) -> None:
        paint_cache_key = self._get_paint_cache_key()
        if paint_cache_key != self._last_paint_cache_key:
            self._last_paint_cache_key = paint_cache_key
            self.update()

    def _get_paint_cache_key(self) -> int:
        raise NotImplementedError("not implemented")

    @property
    def _view(self) -> AudioViewApi:
        return self._api.audio.view

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_data:
            self.setCursor(QtCore.Qt.SizeHorCursor)
            self._apply_drag(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self.end_drag_mode()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & QtCore.Qt.ControlModifier:
            self._zoomed(
                event.angleDelta().y(), event.pos().x() / self.width()
            )
        else:
            self._scrolled(event.angleDelta().y())

    def begin_drag_mode(
        self, drag_mode: DragMode, event: QtGui.QMouseEvent
    ) -> None:
        self._api.undo.begin_capture()

        if drag_mode in {DragMode.NewSubtitleStart, DragMode.NewSubtitleEnd}:
            pts = self.pts_from_x(event.x())
            _create_new_subtitle(
                self._api, pts, before=drag_mode == DragMode.NewSubtitleStart
            )
        else:
            self._drag_data = DragData(
                drag_mode, self._api.subs.selected_events[:]
            )
            self._apply_drag(event)

    def end_drag_mode(self) -> None:
        self._drag_data = None
        self.setCursor(QtCore.Qt.ArrowCursor)
        self._api.undo.end_capture()

    def _apply_drag(self, event: QtGui.QMouseEvent) -> None:
        pts = self.pts_from_x(event.x())

        if self._drag_data.mode == DragMode.SelectionStart:
            self._view.select(
                min(self._view.selection_end, pts), self._view.selection_end
            )

        elif self._drag_data.mode == DragMode.SelectionEnd:
            self._view.select(
                self._view.selection_start,
                max(self._view.selection_start, pts),
            )

        elif self._drag_data.mode == DragMode.VideoPosition:
            self._api.playback.seek(pts)

        elif self._drag_data.mode == DragMode.AudioView:
            old_center = self._view.view_start + self._view.view_size / 2
            new_center = pts
            distance = new_center - old_center
            self._view.move_view(int(distance))

        elif self._drag_data.mode == DragMode.SubtitleStart:
            pts = self._api.video.align_pts_to_near_frame(pts)
            for ass_event in self._drag_data.selected_events:
                ass_event.start = pts
                if ass_event.start > ass_event.end:
                    ass_event.end, ass_event.start = (
                        ass_event.start,
                        ass_event.end,
                    )
            self._view.select(pts, self._view.selection_end)

        elif self._drag_data.mode == DragMode.SubtitleEnd:
            pts = self._api.video.align_pts_to_near_frame(pts)
            for ass_event in self._drag_data.selected_events:
                ass_event.end = pts
                if ass_event.start > ass_event.end:
                    ass_event.end, ass_event.start = (
                        ass_event.start,
                        ass_event.end,
                    )
            self._view.select(self._view.selection_start, pts)

    def _zoomed(self, delta: int, mouse_x: int) -> None:
        if not self._view.size:
            return
        cur_factor = self._view.view_size / self._view.size
        new_factor = cur_factor * (1.1 if delta < 0 else 0.9)
        self._view.zoom_view(new_factor, mouse_x)

    def _scrolled(self, delta: int) -> None:
        if not self._view.size:
            return
        distance = self._view.view_size * 0.05
        distance *= 1 if delta < 0 else -1
        self._view.move_view(int(distance))

    def _draw_frame(self, painter: QtGui.QPainter, bottom_line: bool) -> None:
        painter.setPen(
            QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine)
        )
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(
            0,
            0,
            painter.viewport().width() - 1,
            painter.viewport().height() - (1 if bottom_line else 0),
        )

    def pts_to_x(self, pts: int) -> float:
        raise NotImplementedError("not implemented")

    def pts_from_x(self, x: float) -> int:
        raise NotImplementedError("not implemented")


class BaseLocalAudioWidget(BaseAudioWidget):
    def pts_to_x(self, pts: int) -> float:
        scale = self.width() / max(1, self._view.view_size)
        return (pts - self._view.view_start) * scale

    def pts_from_x(self, x: float) -> float:
        scale = self._view.view_size / self.width()
        return x * scale + self._view.view_start


class BaseGlobalAudioWidget(BaseAudioWidget):
    def pts_to_x(self, pts: int) -> float:
        scale = T.cast(int, self.width()) / max(1, self._view.size)
        return (pts - self._view.min) * scale

    def pts_from_x(self, x: float) -> float:
        scale = self._view.size / self.width()
        return int(x * scale + self._view.min)
