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
from typing import TYPE_CHECKING, Any, Literal, Optional, Union

import ffms2
import numpy as np
from ass_parser import AssEvent
from ass_tag_parser import ass_to_plaintext
from PyQt5.QtCore import QEvent, QObject, QPoint, Qt, pyqtSignal
from PyQt5.QtGui import (
    QBrush,
    QCursor,
    QFont,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QPolygonF,
    QResizeEvent,
)
from PyQt5.QtWidgets import QApplication, QWidget
from sortedcontainers import SortedDict

from bubblesub.api import Api
from bubblesub.api.audio_stream import AudioStream
from bubblesub.api.threading import QueueWorker
from bubblesub.errors import ResourceUnavailable
from bubblesub.ui.audio.base import SLIDER_SIZE, BaseLocalAudioWidget, DragMode
from bubblesub.ui.themes import ThemeManager
from bubblesub.ui.util import blend_colors
from bubblesub.util import chunks

try:
    import pyfftw
except ImportError:
    pyfftw = None


DERIVATION_SIZE = 10
DERIVATION_DISTANCE = 6
CHUNK_SIZE = 50


if TYPE_CHECKING:
    # pylint: disable=unsubscriptable-object
    SpectrumColumn = np.ndarray[Literal[1], "np.dtype[np.uint8]"]
else:
    # prevent runtime TypeError: 'numpy._DTypeMeta' object is not subscriptable
    SpectrumColumn = Any


class SpectrumWorkerSignals(QObject):
    finished = pyqtSignal()


class SpectrumWorker(QueueWorker):
    def __init__(self, api: Api) -> None:
        super().__init__(api.log)
        self.signals = SpectrumWorkerSignals()
        self._api = api

        self.cache: dict[int, SpectrumColumn] = SortedDict()

        if pyfftw is not None:
            self._input = pyfftw.empty_aligned(
                2 << DERIVATION_SIZE, dtype=np.float32
            )
            self._output = pyfftw.empty_aligned(
                (1 << DERIVATION_SIZE) + 1, dtype=np.complex64
            )
            self._fftw = pyfftw.FFTW(
                self._input, self._output, flags=("FFTW_MEASURE",)
            )
        else:
            self._input = np.empty(2 << DERIVATION_SIZE, dtype=np.float32)
            self._output = np.empty(
                (1 << DERIVATION_SIZE) + 1, dtype=np.complex64
            )
            self._fftw = None

    def _process_task(self, task: Any) -> None:
        anything_changed = False
        for block_idx in task:
            out = self._get_spectrogram_for_block_idx(block_idx)
            if out is not None:
                self.cache[block_idx] = out
                anything_changed = True
        if anything_changed:
            self.signals.finished.emit()

    def _get_spectrogram_for_block_idx(
        self, block_idx: int
    ) -> Optional[SpectrumColumn]:
        if self._fftw is None:
            return None

        try:
            audio_stream = self._api.audio.current_stream
            video_stream = self._api.video.current_stream

            first_sample = block_idx << DERIVATION_DISTANCE
            sample_count = 2 << DERIVATION_SIZE

            if video_stream and video_stream.timecodes:
                first_sample -= (
                    video_stream.timecodes[0]
                    * audio_stream.sample_rate
                    // 1000
                )
            first_sample = max(first_sample, 0)

            samples = audio_stream.get_samples(first_sample, sample_count)
            samples = np.mean(samples, axis=1)
            sample_fmt = audio_stream.sample_format

            if sample_fmt == ffms2.FFMS_FMT_S16:
                samples /= 32768.0
            elif sample_fmt == ffms2.FFMS_FMT_S32:
                samples /= 4_294_967_296.0
            elif sample_fmt not in (ffms2.FFMS_FMT_FLT, ffms2.FFMS_FMT_DBL):
                raise RuntimeError(f"unknown sample format: {sample_fmt}")

            self._input[0 : len(samples)] = samples

            out = self._fftw()

            scale_factor = 9 / np.sqrt(2 * (2 << DERIVATION_SIZE))
            out = np.log10(
                np.sqrt(
                    np.real(out) * np.real(out) + np.imag(out) * np.imag(out)
                )
                * scale_factor
                + 1
            )

            out *= int(255 * self._api.playback.volume / 100)
            out = np.clip(out, 0, 255)
            out = np.flip(out, axis=0)
            out = out.astype(dtype=np.uint8)
            return out
        except ResourceUnavailable:
            return None


class SubtitleRect:
    text_margin = 4

    def __init__(
        self,
        painter: QPainter,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        event: AssEvent,
        is_selected: bool,
    ) -> None:
        self.event = event
        self.text_width = painter.fontMetrics().width(self.text)
        self.text_height = painter.fontMetrics().capHeight()
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
        self.label_x1 = x1
        self.label_y1 = y1
        self.label_x2 = x1 + min(
            x2 - x1, self.text_margin * 2 + self.text_width
        )
        self.label_y2 = self.text_margin * 2 + self.text_height
        self.label_is_visible = (
            x2 - x1
        ) >= 2 * self.text_margin + self.text_width
        self.is_selected = is_selected

    @property
    def label_text_x(self) -> int:
        return self.label_x1 + self.text_margin

    @property
    def label_text_y(self) -> int:
        return self.label_y1 + self.text_margin

    @property
    def text(self) -> str:
        return str(self.event.number)


class AudioPreview(BaseLocalAudioWidget):
    def __init__(
        self, api: Api, theme_mgr: ThemeManager, parent: QWidget
    ) -> None:
        super().__init__(api, parent)
        self._theme_mgr = theme_mgr

        self.setMinimumHeight(int(SLIDER_SIZE * 1.5))
        self._rects: list[SubtitleRect] = []

        self._mouse_pos: Optional[QPoint] = None
        self._color_table: list[int] = []
        self._pixels: np.ndarray = np.zeros([0, 0], dtype=np.uint8)

        self._generate_color_table()

        self.setMouseTracking(True)

        app = QApplication.instance()
        assert app
        app.installEventFilter(self)

        api.audio.stream_loaded.connect(self._on_audio_state_change)
        api.audio.stream_unloaded.connect(self._on_audio_state_change)
        api.audio.current_stream_switched.connect(self._on_audio_state_change)
        api.audio.view.view_changed.connect(self._on_audio_view_change)

        api.audio.view.selection_changed.connect(self.repaint_if_needed)
        api.playback.current_pts_changed.connect(
            self.repaint, Qt.ConnectionType.DirectConnection
        )
        api.subs.loaded.connect(self._on_subs_load)
        api.playback.volume_changed.connect(self._on_volume_change)
        api.gui.terminated.connect(self.shutdown)

        self._spectrum_worker = SpectrumWorker(self._api)
        self._api.threading.schedule_runnable(self._spectrum_worker)
        self._spectrum_worker.signals.finished.connect(self.repaint)

        self._show_text_on_spectrogram = api.cfg.opt["audio"][
            "show_text_on_spectrogram"
        ]

    def _on_subs_load(self) -> None:
        self._api.subs.events.changed.subscribe(
            lambda _event: self.repaint_if_needed()
        )

    def shutdown(self) -> None:
        self._spectrum_worker.stop()

    def _get_paint_cache_key(self) -> int:
        with self._api.video.stream_lock:
            return hash(
                (
                    # subtitle rectangles
                    tuple(
                        (event.start, event.end, event.text)
                        for event in self._api.subs.events
                    ),
                    # frames, keyframes
                    (
                        self._api.video.current_stream.uid
                        if self._api.video.has_current_stream
                        else None
                    ),
                    # audio view
                    self._api.audio.view.view_start,
                    self._api.audio.view.view_end,
                    # audio selection
                    self._api.audio.view.selection_start,
                    self._api.audio.view.selection_end,
                    # video position
                    self._api.playback.current_pts,
                    # volume
                    self._api.playback.volume,
                )
            )

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if event.type() in {QEvent.Type.KeyPress, QEvent.Type.KeyRelease}:
            assert isinstance(event, (QKeyEvent, QMouseEvent))
            self._update_cursor(event)
        if event.type() in {QEvent.Type.Enter, QEvent.Type.Leave}:
            self._update_cursor(None)
        return False

    def changeEvent(self, event: QEvent) -> None:
        self._generate_color_table()

    def resizeEvent(self, event: QResizeEvent) -> None:
        height = (1 << DERIVATION_SIZE) + 1
        self._pixels = np.zeros([height, self.width()], dtype=np.uint8)
        self._schedule_current_audio_view()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)

        try:
            self._recompute_rects(painter)
            self._draw_spectrogram(painter)
            self._draw_subtitle_rects(painter)
            self._draw_selection(painter)
            self._draw_frame(painter, bottom_line=False)
            self._draw_keyframes(painter)
            self._draw_video_pos(painter)
            self._draw_mouse(painter)
        finally:
            painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

        if (
            event.button() == Qt.MouseButton.LeftButton
            and not shift
            and not ctrl
        ):
            for rect in self._rects:
                if (
                    rect.label_x1 <= event.x() <= rect.label_x2
                    and rect.label_y1 <= event.y() <= rect.label_y2
                ):
                    self._api.subs.selected_indexes = [rect.event.index]
                    return

        if event.button() == Qt.MouseButton.LeftButton:
            self.begin_drag_mode(
                DragMode.SUBTITLE_START
                if shift
                else DragMode.NEW_SUBTITLE_START
                if ctrl
                else DragMode.SELECTION_START,
                event,
            )
        elif event.button() == Qt.MouseButton.RightButton:
            self.begin_drag_mode(
                DragMode.SUBTITLE_END
                if shift
                else DragMode.NEW_SUBTITLE_END
                if ctrl
                else DragMode.SELECTION_END,
                event,
            )
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.begin_drag_mode(
                DragMode.SUBTITLE_SPLIT if ctrl else DragMode.VIDEO_POSITION,
                event,
            )
            self.end_drag_mode()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._update_cursor(event)
        super().mouseMoveEvent(event)

    def _generate_color_table(self) -> None:
        self._color_table = [
            blend_colors(
                self.palette().window().color(),
                self.palette().text().color(),
                i / 255,
            )
            for i in range(256)
        ]
        self._pens = {
            color: QPen(
                self._theme_mgr.get_color(color), 1, Qt.PenStyle.SolidLine
            )
            for color in self._theme_mgr.current_theme.palette.keys()
        }
        self._brushes = {
            color: QBrush(self._theme_mgr.get_color(color))
            for color in self._theme_mgr.current_theme.palette.keys()
        }

    def _on_volume_change(self) -> None:
        self._spectrum_worker.cache.clear()
        self._schedule_current_audio_view()

    def _on_audio_view_change(self) -> None:
        self._schedule_current_audio_view()

    def _schedule_current_audio_view(self) -> None:
        try:
            delay = self._api.audio.current_stream.delay
            sample_rate = self._api.audio.current_stream.sample_rate
        except ResourceUnavailable:
            delay = 0
            sample_rate = 0

        self.repaint_if_needed()
        self._spectrum_worker.clear_tasks()

        min_pts = self.pts_from_x(0)
        max_pts = self.pts_from_x(self.width() * 2 - 1)
        min_pts -= delay
        max_pts -= delay

        pts_range = np.linspace(min_pts, max_pts, self.width())
        block_idx_range = np.round(pts_range * sample_rate / 1000.0).astype(
            dtype=np.int32
        ) // (2**DERIVATION_DISTANCE)

        blocks_to_update = [
            block_idx
            for block_idx in block_idx_range
            if block_idx not in self._spectrum_worker.cache
        ]
        for chunk in chunks(blocks_to_update, size=CHUNK_SIZE):
            self._spectrum_worker.schedule_task(reversed(chunk))

    def _on_audio_state_change(self, stream: AudioStream) -> None:
        self._spectrum_worker.cache.clear()
        self._schedule_current_audio_view()

    def _draw_spectrogram(self, painter: QPainter) -> None:
        pixels = self._pixels.transpose()
        zero_column = np.zeros([pixels.shape[1]], dtype=np.uint8)
        try:
            delay = self._api.audio.current_stream.delay
            sample_rate = self._api.audio.current_stream.sample_rate
        except ResourceUnavailable:
            delay = 0
            sample_rate = 0

        cached_blocks = (
            list(self._spectrum_worker.cache.keys())
            if self._spectrum_worker
            else []
        )

        min_pts = self.pts_from_x(0)
        max_pts = self.pts_from_x(self.width() - 1)
        min_pts -= delay
        max_pts -= delay

        pts_range = np.linspace(min_pts, max_pts, self.width())
        block_idx_range = np.round(pts_range * sample_rate / 1000.0).astype(
            dtype=np.int32
        ) // (2**DERIVATION_DISTANCE)

        for x, block_idx in enumerate(block_idx_range):
            column = zero_column

            column = self._spectrum_worker.cache.get(block_idx, zero_column)

            if cached_blocks and column is zero_column:
                tmp = bisect.bisect_left(cached_blocks, block_idx)
                if tmp == len(cached_blocks):
                    tmp -= 1
                nearest_block_idx = cached_blocks[tmp]
                column = self._spectrum_worker.cache[nearest_block_idx]

            pixels[x] = column

        image = QImage(
            self._pixels.data,
            self._pixels.shape[1],
            self._pixels.shape[0],
            self._pixels.strides[0],  # pylint: disable=unsubscriptable-object
            QImage.Format_Indexed8,
        )
        image.setColorTable(self._color_table)
        painter.save()
        painter.scale(1, painter.viewport().height() / (pixels.shape[1] - 1))
        painter.drawPixmap(0, 0, QPixmap.fromImage(image))
        painter.restore()

    def _draw_keyframes(self, painter: QPainter) -> None:
        h = painter.viewport().height()
        painter.setPen(self._pens["spectrogram/keyframe"])
        try:
            keyframes = self._api.video.current_stream.keyframes
            timecodes = self._api.video.current_stream.timecodes
        except ResourceUnavailable:
            return
        for keyframe in keyframes:
            timecode = timecodes[keyframe]
            x = round(self.pts_to_x(timecode))
            painter.drawLine(x, 0, x, h)

    def _recompute_rects(self, painter: QPainter) -> None:
        self._rects[:] = []

        h = painter.viewport().height()
        for i, event in enumerate(self._api.subs.events):
            x1 = round(self.pts_to_x(event.start))
            x2 = round(self.pts_to_x(event.end))
            if x1 > x2:
                x1, x2 = x2, x1
            if x2 < 0 or x1 >= self.width():
                continue

            is_selected = i in self._api.subs.selected_indexes
            self._rects.append(
                SubtitleRect(
                    painter, x1, 0, x2, h, event=event, is_selected=is_selected
                )
            )

    def _draw_subtitle_rects(self, painter: QPainter) -> None:
        painter.setFont(QFont(self.font().family(), 10))

        for rect in self._rects:
            prefix = "selected" if rect.is_selected else "unselected"

            if rect.label_is_visible:
                painter.setPen(self._pens[f"spectrogram/{prefix}-label-line"])
                painter.setBrush(
                    self._brushes[f"spectrogram/{prefix}-label-fill"]
                )
                painter.drawRect(
                    rect.label_x1,
                    rect.label_y1,
                    rect.label_x2 - rect.label_x1,
                    rect.label_y2 - rect.label_y1,
                )

            painter.setPen(self._pens[f"spectrogram/{prefix}-sub-line"])
            painter.setBrush(self._brushes[f"spectrogram/{prefix}-sub-fill"])
            painter.drawRect(
                rect.x1, rect.y1, rect.x2 - rect.x1, rect.y2 - rect.y1
            )

            if rect.label_is_visible:
                painter.setPen(self._pens[f"spectrogram/{prefix}-label-text"])
                painter.drawText(
                    rect.label_text_x,
                    rect.label_text_y + rect.text_height,
                    rect.text,
                )

                if self._show_text_on_spectrogram:
                    painter.setPen(
                        self._pens[f"spectrogram/{prefix}-sub-text"]
                    )
                    painter.drawText(
                        rect.label_x2 + rect.text_margin,
                        rect.label_y1,
                        rect.x2 - rect.label_x2 - rect.text_margin * 2,
                        rect.y2 - rect.label_y2,
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignTop
                        | Qt.TextFlag.TextWordWrap,
                        ass_to_plaintext(rect.event.text).replace("\n", " "),
                    )

    def _draw_selection(self, painter: QPainter) -> None:
        h = self.height()
        color_key = (
            "spectrogram/focused-sel"
            if self.parent().hasFocus()
            else "spectrogram/unfocused-sel"
        )
        painter.setPen(self._pens[f"{color_key}-line"])
        painter.setBrush(self._brushes[f"{color_key}-fill"])
        x1 = round(self.pts_to_x(self._view.selection_start))
        x2 = round(self.pts_to_x(self._view.selection_end))
        painter.drawRect(x1, 0, x2 - x1, h)

    def _draw_video_pos(self, painter: QPainter) -> None:
        if not self._api.playback.current_pts:
            return
        x = round(self.pts_to_x(self._api.playback.current_pts))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._brushes["spectrogram/video-marker"])

        width = 7
        polygon = QPolygonF()
        for x, y in [
            (x - width // 2, 0),
            (x + width // 2, 0),
            (x + 1, width // 2),
            (x + 1, painter.viewport().height() - 1),
            (x, painter.viewport().height() - 1),
            (x, width // 2),
            (x - width // 2, 0),
        ]:
            polygon.append(QPoint(x, y))

        painter.drawPolygon(polygon)

    def _draw_mouse(self, painter: QPainter) -> None:
        if not self._mouse_pos:
            return
        pts = self.pts_from_x(self._mouse_pos.x())
        try:
            pts = self._api.video.current_stream.align_pts_to_near_frame(pts)
        except ResourceUnavailable:
            pass
        x = round(self.pts_to_x(pts))

        painter.setPen(self._pens["spectrogram/mouse-marker"])
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(x, 0, x, painter.viewport().height())

    def _update_cursor(
        self, event: Union[QKeyEvent, QMouseEvent, None]
    ) -> None:
        pos = self.mapFromGlobal(QCursor().pos())

        if self._mouse_pos:
            pts = self.pts_from_x(self._mouse_pos.x())
            try:
                pts = self._api.video.current_stream.align_pts_to_near_frame(
                    pts
                )
            except ResourceUnavailable:
                pass
            x = int(self.pts_to_x(pts))
            self.update(x, 0, x, self.height())

        self._mouse_pos = pos if self.geometry().contains(pos) else None

        if self._mouse_pos:
            pts = self.pts_from_x(self._mouse_pos.x())
            try:
                pts = self._api.video.current_stream.align_pts_to_near_frame(
                    pts
                )
            except ResourceUnavailable:
                pass
            x = int(self.pts_to_x(pts))
            self.update(x, 0, x, self.height())

        if self._drag_mode or not event:
            return

        # using QApplication.keyboardModifiers() is unreliable,
        # as it doesn't hold up to date values (at least on X11)
        modifiers = event.modifiers()
        if modifiers == Qt.KeyboardModifier.ShiftModifier:
            self.setCursor(Qt.CursorShape.SplitHCursor)
        elif modifiers == Qt.KeyboardModifier.ControlModifier:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif any(
            rect.label_x1 <= pos.x() <= rect.label_x2
            and rect.label_y1 <= pos.y() <= rect.label_y2
            for rect in self._rects
        ):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
