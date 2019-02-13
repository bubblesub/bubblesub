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

import ffms
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.playback import PlaybackFrontendState
from bubblesub.ui.audio.base import SLIDER_SIZE, BaseLocalAudioWidget, DragMode
from bubblesub.ui.util import blend_colors
from bubblesub.util import chunks
from bubblesub.worker import Worker

try:
    import pyfftw
except ImportError:
    pyfftw = None


DERIVATION_SIZE = 10
DERIVATION_DISTANCE = 6
NOT_CACHED = object()
CACHING = object()
CHUNK_SIZE = 50


class SpectrumWorker(Worker):
    def __init__(self, api: Api) -> None:
        super().__init__()
        self._api = api
        self._input: T.Any = None
        self._output: T.Any = None
        self._fftw: T.Any = None

    def _start_work(self) -> None:
        self._input = pyfftw.empty_aligned(
            2 << DERIVATION_SIZE, dtype=np.float32
        )
        self._output = pyfftw.empty_aligned(
            (1 << DERIVATION_SIZE) + 1, dtype=np.complex64
        )
        self._fftw = pyfftw.FFTW(
            self._input, self._output, flags=("FFTW_MEASURE",)
        )

    def _do_work(self, task: T.Any) -> T.Any:
        chunk = task
        response = []
        for pts in chunk:
            out = self._get_spectrogram_for_pts(pts)
            response.append((pts, out))
        return response

    def _get_spectrogram_for_pts(self, pts: int) -> np.array:
        audio_frame = int(pts * self._api.audio.sample_rate / 1000.0)
        first_sample = (
            audio_frame >> DERIVATION_DISTANCE
        ) << DERIVATION_DISTANCE
        sample_count = 2 << DERIVATION_SIZE

        samples = self._api.audio.get_samples(first_sample, sample_count)
        samples = np.mean(samples, axis=1)
        sample_fmt = self._api.audio.sample_format
        if sample_fmt is None:
            return np.zeros((1 << DERIVATION_SIZE) + 1)

        if sample_fmt == ffms.FFMS_FMT_S16:
            samples /= 32768.0
        elif sample_fmt == ffms.FFMS_FMT_S32:
            samples /= 4_294_967_296.0
        elif sample_fmt not in (ffms.FFMS_FMT_FLT, ffms.FFMS_FMT_DBL):
            raise RuntimeError(f"unknown sample format: {sample_fmt}")

        assert self._input is not None
        self._input[0 : len(samples)] = samples

        assert self._fftw is not None
        out = self._fftw()

        scale_factor = 9 / np.sqrt(1 * (1 << DERIVATION_SIZE))
        out = np.log(
            np.sqrt(np.real(out) * np.real(out) + np.imag(out) * np.imag(out))
            * scale_factor
            + 1
        )

        out *= 255
        out = np.clip(out, 0, 255)
        out = np.flip(out, axis=0)
        out = out.astype(dtype=np.uint8)
        return out


class AudioPreview(BaseLocalAudioWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(api, parent)
        self.setMinimumHeight(int(SLIDER_SIZE * 1.5))
        self._spectrum_worker: T.Optional[SpectrumWorker] = None

        self._spectrum_cache: T.Dict[int, T.List[int]] = {}
        self._need_repaint = False
        self._color_table: T.List[int] = []
        self._pixels: np.array = np.zeros([0, 0], dtype=np.uint8)

        self._generate_color_table()

        timer = QtCore.QTimer(self)
        timer.setInterval(api.cfg.opt["audio"]["spectrogram_sync_interval"])
        timer.timeout.connect(self._repaint_if_needed)
        timer.start()

        api.playback.current_pts_changed.connect(self.update)
        api.playback.state_changed.connect(self._on_playback_state_change)
        api.audio.view.view_changed.connect(self._on_audio_view_change)

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

        painter.end()

        self._need_repaint = False

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.begin_drag_mode(DragMode.SelectionStart, event)
        elif event.button() == QtCore.Qt.RightButton:
            self.begin_drag_mode(DragMode.SelectionEnd, event)
        elif event.button() == QtCore.Qt.MiddleButton:
            self.begin_drag_mode(DragMode.VideoPosition, event)
            self.end_drag_mode()

    def _generate_color_table(self) -> None:
        self._color_table = [
            blend_colors(
                self.palette().window().color(),
                self.palette().text().color(),
                i / 255,
            )
            for i in range(256)
        ]

    def _repaint_if_needed(self) -> None:
        if self._need_repaint:
            self.update()

    def _on_audio_view_change(self) -> None:
        self._schedule_current_audio_view()

    def _schedule_current_audio_view(self) -> None:
        if not self._spectrum_worker:
            return

        self._need_repaint = True
        self.update()

        self._spectrum_cache = {
            key: value
            for key, value in self._spectrum_cache.items()
            if value is not CACHING
        }
        self._spectrum_worker.clear_tasks()

        horizontal_res = self._api.cfg.opt["audio"]["spectrogram_resolution"]
        max_pts = self._api.playback.max_pts

        pts_to_update = set()
        for x in range(self.width() * 2):
            pts = self.pts_from_x(x)
            pts = (pts // horizontal_res) * horizontal_res
            if pts < 0 or (max_pts and pts >= max_pts):
                continue
            if pts not in self._spectrum_cache:
                pts_to_update.add(pts)

        # since the task queue is a LIFO queue, in order to render the columns
        # left-to-right, they need to be iterated backwards (hence reversed()).
        for chunk in chunks(
            list(sorted(pts_to_update, reverse=True)), CHUNK_SIZE
        ):
            self._spectrum_worker.schedule_task(reversed(chunk))
            for pts in chunk:
                self._spectrum_cache[pts] = CACHING

    def _on_playback_state_change(self, state: PlaybackFrontendState) -> None:
        if state == PlaybackFrontendState.Unloaded:
            self._spectrum_cache.clear()
            if self._spectrum_worker:
                self._spectrum_worker.task_finished.disconnect(
                    self._on_spectrum_update
                )
                self._spectrum_worker.clear_tasks()
                self._spectrum_worker.stop()
                self._spectrum_worker = None

        elif state == PlaybackFrontendState.Loading and pyfftw:
            self._spectrum_worker = SpectrumWorker(self._api)
            self._spectrum_worker.task_finished.connect(
                self._on_spectrum_update
            )
            self._spectrum_worker.start()

        self._schedule_current_audio_view()

    def _on_spectrum_update(
        self, response: T.List[T.Tuple[int, T.List[int]]]
    ) -> None:
        for pts, column in response:
            self._spectrum_cache[pts] = column
        self._need_repaint = True

    def _draw_spectrogram(self, painter: QtGui.QPainter) -> None:
        horizontal_res = self._api.cfg.opt["audio"]["spectrogram_resolution"]

        pixels = self._pixels.transpose()
        prev_column = np.zeros([pixels.shape[1]], dtype=np.uint8)
        for x in range(pixels.shape[0]):
            pts = self.pts_from_x(x)
            pts = (pts // horizontal_res) * horizontal_res
            column = self._spectrum_cache.get(pts, NOT_CACHED)
            if column is NOT_CACHED or column is CACHING:
                column = prev_column
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

    def _draw_keyframes(self, painter: QtGui.QPainter) -> None:
        h = painter.viewport().height()
        color = self._api.gui.get_color("spectrogram/keyframe")
        painter.setPen(QtGui.QPen(color, 1, QtCore.Qt.SolidLine))
        for keyframe in self._api.video.keyframes:
            timecode = self._api.video.timecodes[keyframe]
            x = self.pts_to_x(timecode)
            painter.drawLine(x, 0, x, h)

    def _draw_subtitle_rects(self, painter: QtGui.QPainter) -> None:
        h = painter.viewport().height()
        label_height = painter.fontMetrics().capHeight()

        painter.setFont(QtGui.QFont(self.font().family(), 10))

        for i, line in enumerate(self._api.subs.events):
            x1 = self.pts_to_x(line.start)
            x2 = self.pts_to_x(line.end)
            if x2 < 0 or x1 >= self.width():
                continue

            is_selected = i in self._api.subs.selected_indexes
            color_key = "selected" if is_selected else "unselected"

            rect_width = x2 - x1
            label_text = str(line.number)
            label_margin = 4
            label_width = painter.fontMetrics().width(label_text)
            is_label_visible = rect_width >= 2 * label_margin + label_width

            painter.setPen(
                QtGui.QPen(
                    self._api.gui.get_color(
                        f"spectrogram/{color_key}-sub-line"
                    ),
                    1,
                    QtCore.Qt.SolidLine,
                )
            )

            if is_label_visible or is_selected:
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
                    x1,
                    0,
                    min(x2 - x1, label_margin * 2 + label_width),
                    label_margin * 2 + label_height,
                )

            painter.setBrush(
                QtGui.QBrush(
                    self._api.gui.get_color(
                        f"spectrogram/{color_key}-sub-fill"
                    )
                )
            )
            painter.drawRect(x1, 0, x2 - x1, h - 1)

            if is_label_visible:
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
                    x1 + label_margin, label_height + label_margin, label_text
                )

    def _draw_selection(self, painter: QtGui.QPainter) -> None:
        if not self._view.has_selection:
            return
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
        x1 = self.pts_to_x(self._view.selection_start)
        x2 = self.pts_to_x(self._view.selection_end)
        painter.drawRect(x1, 0, x2 - x1, h - 1)

    def _draw_video_pos(self, painter: QtGui.QPainter) -> None:
        if not self._api.playback.current_pts:
            return
        x = self.pts_to_x(self._api.playback.current_pts)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._api.gui.get_color("spectrogram/video-marker"))

        width = 7
        polygon = QtGui.QPolygonF()
        for x, y in [
            (x - width / 2, 0),
            (x + width / 2, 0),
            (x + 1, width / 2),
            (x + 1, painter.viewport().height() - 1),
            (x, painter.viewport().height() - 1),
            (x, width / 2),
            (x - width / 2, 0),
        ]:
            polygon.append(QtCore.QPointF(x, y))

        painter.drawPolygon(polygon)
