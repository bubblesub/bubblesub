from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui
import bubblesub.util
from bubblesub.ui.util import blend_colors
from bubblesub.ui.spectrogram import SpectrumProvider, DERIVATION_SIZE


# TODO: audio selection
# TODO: draw position of video frame


class AudioPreviewWidget(QtWidgets.QWidget):
    scroll = QtCore.pyqtSignal(int)
    zoom = QtCore.pyqtSignal(int)

    def __init__(self, api):
        super().__init__()
        self._api = api
        self.setMinimumHeight(100)
        self.spectrum = None
        self._need_repaint = False

        timer = QtCore.QTimer(self)
        timer.setInterval(100)
        timer.timeout.connect(self._repaint_if_needed)
        timer.start()

        api.video.loaded.connect(self._video_loaded)

    def paintEvent(self, e):
        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_spectrogram(painter, e)
        painter.end()

        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_scale(painter)
        self._draw_subtitle_rects(painter)
        painter.end()

        self._need_repaint = False

    def _repaint_if_needed(self):
        if self._need_repaint:
            self.repaint()

    def _video_loaded(self):
        # TODO: refactor this
        if self.spectrum is not None:
            self.spectrum.stop()
        self.spectrum = SpectrumProvider(self._api)
        self.spectrum.updated.connect(self._spectrum_updated)

    def _spectrum_updated(self):
        self._need_repaint = True

    def wheelEvent(self, e):
        if e.modifiers() & QtCore.Qt.ControlModifier:
            self.zoom.emit(e.angleDelta().y())
        else:
            self.scroll.emit(e.angleDelta().y())

    def _draw_spectrogram(self, painter, event):
        if self.spectrum is None:
            return
        painter.scale(1, self.height() / (1 << DERIVATION_SIZE))

        color_table = []
        for i in range(256):
            color_table.append(
                blend_colors(
                    self.palette().window().color(),
                    self.palette().text().color(),
                    i / 255))

        # since the task queue is a LIFO queue, in order to render the columns
        # left-to-right, they need to be iterated backwards (hence reversed()).
        for x in reversed(range(self.width())):
            column = self.spectrum.get_fft(self._pts_from_x(x))
            if column is None:
                continue
            image = QtGui.QImage(
                column.data,
                1,
                column.shape[0],
                column.strides[0],
                QtGui.QImage.Format_Indexed8)
            image.setColorTable(color_table)
            painter.drawPixmap(x, 0, QtGui.QPixmap.fromImage(image))

    def _draw_scale(self, painter):
        painter.setFont(QtGui.QFont('Serif', 7, QtGui.QFont.Light))
        w = self.width()
        h = self.height()

        painter.setPen(
            QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(0, 0, w - 1, h - 1)

        one_second = 1000
        one_minute = 60 * one_second

        start_pts = int(self._api.audio.view_start // one_minute) * one_minute
        end_pts = (
            (int(self._api.audio.view_end + one_minute) // one_minute)
            * one_minute)
        seconds_per_pixel = (
            (self._api.audio.view_end - self._api.audio.view_start)
            / self.width() / 1000.0)

        for pts in range(start_pts, end_pts, one_second):
            if pts % one_minute == 0:
                gap = 8
            else:
                gap = 4

            x = self._pts_to_x(pts)
            painter.drawLine(x, 0, x, gap)
            metrics = painter.fontMetrics()
            if pts % one_minute == 0:
                text = '{:02}:{:02}'.format(pts // one_minute, 0)
            elif pts % (10 * one_second) == 0:
                text = '{:02}'.format((pts % one_minute) // one_second)
            else:
                text = ''
            fw = metrics.width(text)
            fh = metrics.height()
            painter.drawText(x, gap + fh, text)

    def _draw_subtitle_rects(self, painter):
        w = self.width()
        h = self.height()
        painter.setPen(
            QtGui.QPen(self.palette().highlight(), 1, QtCore.Qt.SolidLine))
        for i, line in enumerate(self._api.subtitles):
            painter.setBrush(QtGui.QBrush(
                self.palette().highlight().color(),
                QtCore.Qt.FDiagPattern if i & 1 else QtCore.Qt.BDiagPattern))
            x1 = self._pts_to_x(line.start)
            x2 = self._pts_to_x(line.end)
            painter.drawRect(x1, 30, x2 - x1, h - 30)

    def _pts_to_x(self, pts):
        scale = self.width() / max(1, self._api.audio.view_size)
        return (pts - self._api.audio.view_start) * scale

    def _pts_from_x(self, x):
        scale = self._api.audio.view_size / self.width()
        return x * scale + self._api.audio.view_start


class AudioSliderWidget(QtWidgets.QWidget):
    def __init__(self, api):
        super().__init__()
        self.setFixedHeight(20)
        self._api = api

    def paintEvent(self, e):
        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_slider(painter)
        painter.end()

    def _draw_slider(self, painter):
        size = self.size()
        w = size.width()
        h = size.height()

        brush = QtGui.QBrush(self.palette().highlight())
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(brush)
        x1 = self._pts_to_x(self._api.audio.view_start)
        x2 = self._pts_to_x(self._api.audio.view_end)
        painter.drawRect(x1, 0, x2 - x1, h - 1)

        brush = QtGui.QBrush(self.palette().highlight())
        pen = QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(0, 0, w - 1, h - 1)

    def _pts_to_x(self, pts):
        scale = self.width() / max(1, self._api.audio.size)
        return (pts - self._api.audio.min) * scale


class Audio(QtWidgets.QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self._api = api
        self._audio_slider = AudioSliderWidget(self._api)
        self._audio_preview = AudioPreviewWidget(self._api)
        self._audio_preview.zoom.connect(self._audio_preview_zoomed)
        self._audio_preview.scroll.connect(self._audio_preview_scrolled)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self._audio_preview)
        vbox.addWidget(self._audio_slider)
        self.setLayout(vbox)

        api.audio.view_changed.connect(self._audio_view_changed)
        api.grid_selection_changed.connect(self._grid_selection_changed)

    def _audio_view_changed(self):
        self._repaint()

    def _grid_selection_changed(self, rows):
        if len(rows) == 1:
            sub = self._api.subtitles[rows[0]]
            self._api.audio.view(sub.start - 10000, sub.end + 10000)

    def _audio_preview_zoomed(self, delta):
        cur_factor = (
            (self._api.audio.view_end - self._api.audio.view_start) /
            (self._api.audio.max - self._api.audio.min))
        new_factor = cur_factor * (1.1 if delta < 0 else 0.9)
        self._api.audio.zoom(new_factor)
        self._repaint()

    def _audio_preview_scrolled(self, delta):
        distance = 1 if delta < 0 else -1
        distance *= self._api.audio.view_size * 0.05
        self._api.audio.move(distance)
        self._repaint()

    def _repaint(self):
        self._audio_slider.repaint()
        self._audio_preview.repaint()
