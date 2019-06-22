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

import ffms2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.audio import AudioApi, AudioState
from bubblesub.api.log import LogApi
from bubblesub.api.threading import QueueWorker
from bubblesub.fmt.ass.event import AssEvent
from bubblesub.ui.audio.base import SLIDER_SIZE, BaseLocalAudioWidget, DragMode
from bubblesub.ui.util import blend_colors
from bubblesub.util import chunks

try:
    import pyfftw
except ImportError:
    pyfftw = None


DERIVATION_SIZE = 10
DERIVATION_DISTANCE = 6
CHUNK_SIZE = 50


class SpectrumWorkerSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal()


class SpectrumWorker(QueueWorker):
    def __init__(self, log_api: LogApi, audio_api: AudioApi) -> None:
        super().__init__(log_api)
        self.signals = SpectrumWorkerSignals()
        self._audio_api = audio_api

        self.cache: T.Dict[int, T.List[int]] = {}

        self._input = pyfftw.empty_aligned(
            2 << DERIVATION_SIZE, dtype=np.float32
        )
        self._output = pyfftw.empty_aligned(
            (1 << DERIVATION_SIZE) + 1, dtype=np.complex64
        )
        self._fftw = pyfftw.FFTW(
            self._input, self._output, flags=("FFTW_MEASURE",)
        )

    def _process_task(self, task: T.Any) -> None:
        anything_changed = False
        for block_idx in task:
            out = self._get_spectrogram_for_block_idx(block_idx)
            if out is not None:
                self.cache[block_idx] = out
                anything_changed = True
        if anything_changed:
            self.signals.finished.emit()

    def _get_spectrogram_for_block_idx(self, block_idx: int) -> np.array:
        first_sample = block_idx << DERIVATION_DISTANCE
        sample_count = 2 << DERIVATION_SIZE

        samples = self._audio_api.get_samples(first_sample, sample_count)
        samples = np.mean(samples, axis=1)
        sample_fmt = self._audio_api.sample_format
        if sample_fmt is None:
            return None

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
            np.sqrt(np.real(out) * np.real(out) + np.imag(out) * np.imag(out))
            * scale_factor
            + 1
        )

        out *= 255
        out = np.clip(out, 0, 255)
        out = np.flip(out, axis=0)
        out = out.astype(dtype=np.uint8)
        return out


class SubtitleLabel:
    text_margin = 4

    def __init__(
        self, painter: QtGui.QPainter, x1: int, x2: int, event: AssEvent
    ) -> None:
        self.event = event
        self.text_width = painter.fontMetrics().width(self.text)
        self.text_height = painter.fontMetrics().capHeight()
        self.x1 = x1
        self.y1 = 0
        self.x2 = x1 + min(x2 - x1, self.text_margin * 2 + self.text_width)
        self.y2 = self.text_margin * 2 + self.text_height
        self.is_visible = (x2 - x1) >= 2 * self.text_margin + self.text_width

    @property
    def text_x(self) -> int:
        return self.x1 + self.text_margin

    @property
    def text_y(self) -> int:
        return self.y1 + self.text_margin

    @property
    def text(self) -> str:
        return str(self.event.number)


class AudioPreview(BaseLocalAudioWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(api, parent)
        self.setMinimumHeight(int(SLIDER_SIZE * 1.5))
        self._spectrum_worker: T.Optional[SpectrumWorker] = None
        self._labels: T.List[SubtitleLabel] = []

        self._mouse_pos: T.Optional[QtCore.QPoint] = None
        self._need_repaint = False
        self._color_table: T.List[int] = []
        self._pixels: np.array = np.zeros([0, 0], dtype=np.uint8)

        self._generate_color_table()

        timer = QtCore.QTimer(self)
        timer.setInterval(api.cfg.opt["audio"]["spectrogram_sync_interval"])
        timer.timeout.connect(self._repaint_if_needed)
        timer.start()

        self.setMouseTracking(True)
        QtWidgets.QApplication.instance().installEventFilter(self)

        api.playback.current_pts_changed.connect(self.update)
        api.audio.state_changed.connect(self._on_audio_state_change)
        api.audio.view.view_changed.connect(self._on_audio_view_change)

    def eventFilter(
        self, source: QtCore.QObject, event: QtCore.QEvent
    ) -> bool:
        if event.type() in {QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease}:
            self._update_cursor(event)
        if event.type() in {QtCore.QEvent.Enter, QtCore.QEvent.Leave}:
            self._update_cursor(None)
        return False

    def changeEvent(self, event: QtCore.QEvent) -> None:
        self._generate_color_table()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        height = (1 << DERIVATION_SIZE) + 1
        self._pixels = np.zeros([height, self.width()], dtype=np.uint8)
        self._schedule_current_audio_view()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()
        painter.begin(self)

        self._draw_spectrogram(painter)
        self._draw_subtitle_rects(painter)
        self._draw_selection(painter)
        self._draw_frame(painter, bottom_line=False)
        self._draw_keyframes(painter)
        self._draw_video_pos(painter)
        self._draw_mouse(painter)

        painter.end()

        self._need_repaint = False

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            if event.modifiers() & QtCore.Qt.ShiftModifier:
                self.begin_drag_mode(DragMode.SubtitleStart, event)
            elif event.modifiers() & QtCore.Qt.ControlModifier:
                self.begin_drag_mode(DragMode.NewSubtitleStart, event)
            else:
                for label in self._labels:
                    if (
                        label.x1 <= event.x() <= label.x2
                        and label.y1 <= event.y() <= label.y2
                    ):
                        self._api.subs.selected_indexes = [label.event.index]
                        break
                else:
                    self.begin_drag_mode(DragMode.SelectionStart, event)
        elif event.button() == QtCore.Qt.RightButton:
            if event.modifiers() & QtCore.Qt.ShiftModifier:
                self.begin_drag_mode(DragMode.SubtitleEnd, event)
            elif event.modifiers() & QtCore.Qt.ControlModifier:
                self.begin_drag_mode(DragMode.NewSubtitleEnd, event)
            else:
                self.begin_drag_mode(DragMode.SelectionEnd, event)
        elif event.button() == QtCore.Qt.MiddleButton:
            self.begin_drag_mode(DragMode.VideoPosition, event)
            self.end_drag_mode()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
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
        self._mouse_color = self._api.gui.get_color("spectrogram/mouse-marker")

    def _repaint_if_needed(self) -> None:
        if self._need_repaint:
            self.update()

    def _on_audio_view_change(self) -> None:
        self._schedule_current_audio_view()

    def _schedule_current_audio_view(self) -> None:
        self._need_repaint = True
        self.update()

        if not self._spectrum_worker:
            return

        self._spectrum_worker.clear_tasks()

        max_block_idx = self._api.audio.sample_count >> DERIVATION_DISTANCE

        blocks_to_update = set()
        for x in range(self.width() * 2):
            block_idx = self.block_idx_from_x(x)
            if block_idx < 0 or (max_block_idx and block_idx >= max_block_idx):
                continue
            if block_idx not in self._spectrum_worker.cache:
                blocks_to_update.add(block_idx)

        for chunk in chunks(list(sorted(blocks_to_update)), CHUNK_SIZE):
            self._spectrum_worker.schedule_task(reversed(chunk))

    def _on_audio_state_change(self, state: AudioState) -> None:
        if state == AudioState.NotLoaded:
            if self._spectrum_worker:
                self._spectrum_worker.stop()
                self._spectrum_worker = None

        elif state == AudioState.Loading and pyfftw:
            self._spectrum_worker = SpectrumWorker(
                self._api.log, self._api.audio
            )
            self._spectrum_worker.signals.finished.connect(
                self._on_spectrum_update
            )
            self._api.threading.schedule_runnable(self._spectrum_worker)

        self._schedule_current_audio_view()

    def _on_spectrum_update(self) -> None:
        self._need_repaint = True

    def _draw_spectrogram(self, painter: QtGui.QPainter) -> None:
        pixels = self._pixels.transpose()
        prev_column = np.zeros([pixels.shape[1]], dtype=np.uint8)
        for x in range(pixels.shape[0]):
            block_idx = self.block_idx_from_x(x)
            column = prev_column
            if self._spectrum_worker:
                column = self._spectrum_worker.cache.get(
                    block_idx, prev_column
                )
            pixels[x] = column

        image = QtGui.QImage(
            self._pixels.data,
            self._pixels.shape[1],
            self._pixels.shape[0],
            self._pixels.strides[0],
            QtGui.QImage.Format_Indexed8,
        )
        image.setColorTable(self._color_table)
        painter.save()
        painter.scale(1, painter.viewport().height() / (pixels.shape[1] - 1))
        painter.drawPixmap(0, 0, QtGui.QPixmap.fromImage(image))
        painter.restore()

    def block_idx_from_x(self, x) -> int:
        pts = self.pts_from_x(x)
        return (
            int(pts * self._api.audio.sample_rate / 1000.0)
            >> DERIVATION_DISTANCE
        )

    def _draw_keyframes(self, painter: QtGui.QPainter) -> None:
        h = painter.viewport().height()
        color = self._api.gui.get_color("spectrogram/keyframe")
        painter.setPen(QtGui.QPen(color, 1, QtCore.Qt.SolidLine))
        for keyframe in self._api.video.keyframes:
            timecode = self._api.video.timecodes[keyframe]
            x = round(self.pts_to_x(timecode))
            painter.drawLine(x, 0, x, h)

    def _draw_subtitle_rects(self, painter: QtGui.QPainter) -> None:
        self._labels[:] = []

        h = painter.viewport().height()

        painter.setFont(QtGui.QFont(self.font().family(), 10))

        for i, event in enumerate(self._api.subs.events):
            x1 = round(self.pts_to_x(event.start))
            x2 = round(self.pts_to_x(event.end))
            if x1 > x2:
                x1, x2 = x2, x1
            if x2 < 0 or x1 >= self.width():
                continue

            is_selected = i in self._api.subs.selected_indexes
            color_key = "selected" if is_selected else "unselected"

            label = SubtitleLabel(painter, x1, x2, event=event)
            self._labels.append(label)

            painter.setPen(
                QtGui.QPen(
                    self._api.gui.get_color(
                        f"spectrogram/{color_key}-sub-line"
                    ),
                    1,
                    QtCore.Qt.SolidLine,
                )
            )

            if label.is_visible or is_selected:
                painter.setBrush(
                    QtGui.QBrush(
                        self._api.gui.get_color(
                            f"spectrogram/{color_key}-sub-line"
                        )
                        if is_selected
                        else self.palette().window()
                    )
                )
                painter.drawRect(
                    label.x1,
                    label.y1,
                    label.x2 - label.x1,
                    label.y2 - label.y1,
                )

            painter.setBrush(
                QtGui.QBrush(
                    self._api.gui.get_color(
                        f"spectrogram/{color_key}-sub-fill"
                    )
                )
            )
            painter.drawRect(x1, 0, x2 - x1, h - 1)

            if label.is_visible:
                painter.setPen(
                    QtGui.QPen(
                        self._api.gui.get_color(
                            f"spectrogram/{color_key}-sub-text"
                        ),
                        1,
                        QtCore.Qt.SolidLine,
                    )
                )
                painter.drawText(
                    label.text_x, label.text_y + label.text_height, label.text
                )

    def _draw_selection(self, painter: QtGui.QPainter) -> None:
        h = self.height()
        color_key = (
            "spectrogram/focused-sel"
            if self.parent().hasFocus()
            else "spectrogram/unfocused-sel"
        )
        painter.setPen(
            QtGui.QPen(
                self._api.gui.get_color(f"{color_key}-line"),
                1,
                QtCore.Qt.SolidLine,
            )
        )
        painter.setBrush(
            QtGui.QBrush(self._api.gui.get_color(f"{color_key}-fill"))
        )
        x1 = round(self.pts_to_x(self._view.selection_start))
        x2 = round(self.pts_to_x(self._view.selection_end))
        painter.drawRect(x1, 0, x2 - x1, h - 1)

    def _draw_video_pos(self, painter: QtGui.QPainter) -> None:
        if not self._api.playback.current_pts:
            return
        x = round(self.pts_to_x(self._api.playback.current_pts))
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._api.gui.get_color("spectrogram/video-marker"))

        width = 7
        polygon = QtGui.QPolygonF()
        for x, y in [
            (x - width // 2, 0),
            (x + width // 2, 0),
            (x + 1, width // 2),
            (x + 1, painter.viewport().height() - 1),
            (x, painter.viewport().height() - 1),
            (x, width // 2),
            (x - width // 2, 0),
        ]:
            polygon.append(QtCore.QPoint(x, y))

        painter.drawPolygon(polygon)

    def _draw_mouse(self, painter: QtGui.QPainter) -> None:
        if not self._mouse_pos:
            return
        pts = self.pts_from_x(self._mouse_pos.x())
        pts = self._api.video.align_pts_to_near_frame(pts)
        x = round(self.pts_to_x(pts))

        painter.setPen(self._mouse_color)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawLine(x, 0, x, painter.viewport().height())

    def _update_cursor(
        self, event: T.Union[QtGui.QKeyEvent, QtGui.QMouseEvent, None]
    ) -> None:
        pos = self.mapFromGlobal(QtGui.QCursor().pos())

        if self._mouse_pos:
            pts = self.pts_from_x(self._mouse_pos.x())
            pts = self._api.video.align_pts_to_near_frame(pts)
            x = self.pts_to_x(pts)
            self.update(x, 0, x, self.height())

        self._mouse_pos = pos if self.geometry().contains(pos) else None

        if self._mouse_pos:
            pts = self.pts_from_x(self._mouse_pos.x())
            pts = self._api.video.align_pts_to_near_frame(pts)
            x = self.pts_to_x(pts)
            self.update(x, 0, x, self.height())

        if self._drag_data or not event:
            return

        # using QtWidgets.QApplication.keyboardModifiers() is unreliable,
        # as it doesn't hold up to date values (at least on X11)
        modifiers = event.modifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self.setCursor(QtCore.Qt.SplitHCursor)
        elif modifiers == QtCore.Qt.ControlModifier:
            self.setCursor(QtCore.Qt.SizeHorCursor)
        elif any(
            label.x1 <= pos.x() <= label.x2 and label.y1 <= pos.y() <= label.y2
            for label in self._labels
        ):
            self.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            self.setCursor(QtCore.Qt.CrossCursor)
