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
from copy import copy
from dataclasses import dataclass
from typing import Optional, cast

from ass_parser import AssEvent
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMouseEvent, QPainter, QPen, QWheelEvent
from PyQt5.QtWidgets import QWidget

from bubblesub.api import Api
from bubblesub.api.audio_view import AudioViewApi

SLIDER_SIZE = 20


class DragMode(enum.Enum):
    SELECTION_START = 1
    SELECTION_END = 2
    VIDEO_POSITION = 3
    AUDIO_VIEW = 4
    SUBTITLE_START = 5
    SUBTITLE_END = 6
    NEW_SUBTITLE_START = 7
    NEW_SUBTITLE_END = 8
    SUBTITLE_SPLIT = 9


@dataclass
class InsertionPoint:
    idx: int
    start: int
    end: int


def get_subtitle_insertion_point(
    api: Api, pts: int, by_end: bool
) -> InsertionPoint:
    # legend:
    # |---| subtitle
    #   *   pts (where the user clicked)

    default_duration = api.cfg.opt["subs"]["default_duration"]

    if not api.subs.selected_indexes:
        if by_end:
            return InsertionPoint(
                idx=0, start=max(0, pts - default_duration), end=pts
            )
        return InsertionPoint(idx=0, start=pts, end=pts + default_duration)

    sel_start = api.subs.selected_events[0].start
    sel_end = api.subs.selected_events[-1].end

    if by_end:
        # right-click
        if pts >= sel_end:
            # before: |----|  *
            # after:  |----|--|
            return InsertionPoint(
                idx=api.subs.selected_indexes[-1] + 1, start=sel_end, end=pts
            )

        if pts <= sel_start:
            # before:      *  |----|
            # after:  |----|  |----|
            return InsertionPoint(
                idx=api.subs.selected_indexes[0],
                start=pts - default_duration,
                end=pts,
            )
    else:
        # left-click
        if pts >= sel_end:
            # before: |----|  *
            # after:  |----|  |----|
            return InsertionPoint(
                idx=api.subs.selected_indexes[-1] + 1,
                start=pts,
                end=pts + default_duration,
            )

        if pts <= sel_start:
            # before: *  |----|
            # after:  |--|=|--|
            return InsertionPoint(
                idx=api.subs.selected_indexes[0],
                start=pts,
                end=pts + default_duration,
            )

    # before: |--*--|
    # after:  |--|==|-|
    return InsertionPoint(
        idx=api.subs.selected_indexes[0], start=pts, end=pts + default_duration
    )


def create_new_subtitle(api: Api, pts: int, by_end: bool) -> None:
    current_video_stream = api.video.current_stream
    if current_video_stream:
        pts = current_video_stream.align_pts_to_near_frame(pts)
    insertion_point = get_subtitle_insertion_point(api, pts, by_end)
    if current_video_stream:
        insertion_point.start = current_video_stream.align_pts_to_near_frame(
            insertion_point.start
        )
        insertion_point.end = current_video_stream.align_pts_to_near_frame(
            insertion_point.end
        )

    api.subs.events.insert(
        insertion_point.idx,
        AssEvent(
            start=insertion_point.start,
            end=insertion_point.end,
            style_name=api.subs.default_style_name,
        ),
    )
    api.subs.selected_indexes = [insertion_point.idx]


class DragModeExecutor:
    drag_mode = NotImplemented

    def __init__(self, api: Api) -> None:
        self._api = api
        self.selected_events: list[AssEvent] = []

    def begin_drag(self, event: QMouseEvent, pts: int) -> None:
        self.selected_events = self._api.subs.selected_events[:]

    def apply_drag(self, event: QMouseEvent, pts: int) -> None:
        pass

    def end_drag(self) -> None:
        self._api.undo.push()


class SelectionStartDragModeExecutor(DragModeExecutor):
    drag_mode = DragMode.SELECTION_START

    def apply_drag(self, event: QMouseEvent, pts: int) -> None:
        return self._api.audio.view.select(
            min(self._api.audio.view.selection_end, pts),
            self._api.audio.view.selection_end,
        )


class SelectionEndDragModeExecutor(DragModeExecutor):
    drag_mode = DragMode.SELECTION_END

    def apply_drag(self, event: QMouseEvent, pts: int) -> None:
        self._api.audio.view.select(
            self._api.audio.view.selection_start,
            max(self._api.audio.view.selection_start, pts),
        )


class VideoPositionDragModeExecutor(DragModeExecutor):
    drag_mode = DragMode.VIDEO_POSITION

    def apply_drag(self, event: QMouseEvent, pts: int) -> None:
        self._api.playback.seek(pts)


class AudioViewDragModeExecutor(DragModeExecutor):
    drag_mode = DragMode.AUDIO_VIEW

    def apply_drag(self, event: QMouseEvent, pts: int) -> None:
        old_center = (
            self._api.audio.view.view_start
            + self._api.audio.view.view_size / 2
        )
        new_center = pts
        distance = new_center - old_center
        self._api.audio.view.move_view(int(distance))


class SubtitleStartDragModeExecutor(DragModeExecutor):
    drag_mode = DragMode.SUBTITLE_START

    def apply_drag(self, event: QMouseEvent, pts: int) -> None:
        if self._api.video.current_stream:
            pts = self._api.video.current_stream.align_pts_to_near_frame(pts)
        for ass_event in self.selected_events:
            ass_event.start = pts
            if ass_event.start > ass_event.end:
                ass_event.end, ass_event.start = (
                    ass_event.start,
                    ass_event.end,
                )
        self._api.audio.view.select(pts, self._api.audio.view.selection_end)


class SubtitleEndDragModeExecutor(DragModeExecutor):
    drag_mode = DragMode.SUBTITLE_END

    def apply_drag(self, event: QMouseEvent, pts: int) -> None:
        if self._api.video.current_stream:
            pts = self._api.video.current_stream.align_pts_to_near_frame(pts)
        for ass_event in self.selected_events:
            ass_event.end = pts
            if ass_event.start > ass_event.end:
                ass_event.end, ass_event.start = (
                    ass_event.start,
                    ass_event.end,
                )
        self._api.audio.view.select(self._api.audio.view.selection_start, pts)


class NewSubtitleStartDragModeExecutor(DragModeExecutor):
    drag_mode = DragMode.NEW_SUBTITLE_START

    def begin_drag(self, event: QMouseEvent, pts: int) -> None:
        super().begin_drag(event, pts)
        create_new_subtitle(self._api, pts, by_end=False)


class NewSubtitleEndDragModeExecutor(DragModeExecutor):
    drag_mode = DragMode.NEW_SUBTITLE_END

    def begin_drag(self, event: QMouseEvent, pts: int) -> None:
        super().begin_drag(event, pts)
        create_new_subtitle(self._api, pts, by_end=True)


class SubtitleSplitDragModeExecutor(DragModeExecutor):
    drag_mode = DragMode.SUBTITLE_SPLIT

    def __init__(self, api: Api) -> None:
        super().__init__(api)
        self.source_events: list[AssEvent] = []
        self.copied_events: list[AssEvent] = []

    def begin_drag(self, event: QMouseEvent, pts: int) -> None:
        super().begin_drag(event, pts)
        self.source_events[:] = [
            source_event
            for source_event in self._api.subs.events
            if source_event.start <= pts <= source_event.end
        ]
        self.copied_events[:] = []
        if not self.source_events:
            return
        idx: int
        for source_event in reversed(self.source_events):
            assert source_event.index
            idx = source_event.index
            new_event = copy(source_event)
            self._api.subs.events.insert(idx + 1, new_event)
            self.copied_events.append(new_event)
        self._api.subs.selected_indexes = [idx, idx + 1]

    def apply_drag(self, event: QMouseEvent, pts: int) -> None:
        if self._api.video.current_stream:
            pts = self._api.video.current_stream.align_pts_to_near_frame(pts)
        for ass_event in self.source_events:
            ass_event.end = pts
        for ass_event in self.copied_events:
            ass_event.start = pts


class BaseAudioWidget(QWidget):
    def __init__(self, api: Api, parent: QWidget) -> None:
        super().__init__(parent)
        self._api = api
        self._drag_mode: Optional[DragMode] = None
        self._drag_mode_executors = {
            executor.drag_mode: executor(self._api)
            for executor in DragModeExecutor.__subclasses__()
        }
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

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_mode:
            self.setCursor(Qt.SizeHorCursor)
            self._apply_drag(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.end_drag_mode()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.ControlModifier:
            self._zoomed(
                event.angleDelta().y(), event.pos().x() / self.width()
            )
        else:
            self._scrolled(event.angleDelta().y())

    def begin_drag_mode(self, drag_mode: DragMode, event: QMouseEvent) -> None:
        if self._drag_mode:
            self._drag_mode_executors[self._drag_mode].end_drag()
        pts = self.pts_from_x(event.x())
        self._drag_mode = drag_mode
        self._drag_mode_executors[self._drag_mode].begin_drag(event, pts)
        self._drag_mode_executors[self._drag_mode].apply_drag(event, pts)

    def end_drag_mode(self) -> None:
        self.setCursor(Qt.ArrowCursor)
        if self._drag_mode:
            self._drag_mode_executors[self._drag_mode].end_drag()
            self._drag_mode = None

    def _apply_drag(self, event: QMouseEvent) -> None:
        pts = self.pts_from_x(event.x())
        self._drag_mode_executors[self._drag_mode].apply_drag(event, pts)

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

    def _draw_frame(self, painter: QPainter, bottom_line: bool) -> None:
        painter.setPen(QPen(self.palette().text(), 1, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)
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

    def pts_from_x(self, x: float) -> int:
        scale = self._view.view_size / self.width()
        return int(x * scale + self._view.view_start)

    def _get_paint_cache_key(self) -> int:
        raise NotImplementedError("not implemented")


class BaseGlobalAudioWidget(BaseAudioWidget):
    def pts_to_x(self, pts: int) -> float:
        scale = cast(int, self.width()) / max(1, self._view.size)
        return (pts - self._view.min) * scale

    def pts_from_x(self, x: float) -> int:
        scale = self._view.size / self.width()
        return int(x * scale + self._view.min)

    def _get_paint_cache_key(self) -> int:
        raise NotImplementedError("not implemented")
