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

    def _video_loaded(self):
        if self.spectrum is not None:
            self.spectrum.stop()
        self.spectrum = SpectrumProvider(self._api)
        self.spectrum.updated.connect(self._spectrum_updated)

    def _repaint_if_needed(self):
        if self._need_repaint:
            self.repaint()

    def _spectrum_updated(self):
        self._need_repaint = True

    def wheelEvent(self, e):
        if e.modifiers() & QtCore.Qt.ControlModifier:
            self.zoom.emit(e.angleDelta().y())
        else:
            self.scroll.emit(e.angleDelta().y())

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawSpectrogram(qp, e)
        qp.end()
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()
        self._need_repaint = False

    def drawSpectrogram(self, qp, event):
        if self.spectrum is None:
            return
        qp.scale(1, self.height() / (1 << DERIVATION_SIZE))

        color_table = []
        for i in range(256):
            color_table.append(
                blend_colors(
                    self.palette().window().color(),
                    self.palette().text().color(),
                    i / 255))

        for x in range(self.width()):
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
            qp.drawPixmap(x, 0, QtGui.QPixmap.fromImage(image))

    def drawWidget(self, qp):
        font = QtGui.QFont('Serif', 7, QtGui.QFont.Light)
        qp.setFont(font)
        size = self.size()
        w = size.width()
        h = size.height()

        qp.setPen(QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine))
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawRect(0, 0, w - 1, h - 1)

        one_second = 1000
        one_minute = 60 * one_second

        start_pts = int(self._api.audio.view_start // one_minute) * one_minute
        end_pts = (
            (int(self._api.audio.view_end + one_minute) // one_minute)
            * one_minute)
        seconds_per_pixel = (
            (self._api.audio.view_end - self._api.audio.view_start)
            / self.width() / 1000.0)

        if seconds_per_pixel > 2.5:
            every_nth_minute = 5
        elif seconds_per_pixel > 0.1:
            every_nth_second = 15
        else:
            every_nth_second = 1

        for pts in range(start_pts, end_pts, one_second):
            if pts % one_minute == 0:
                gap = 8
            else:
                gap = 4

            x = self._pts_to_x(pts)
            qp.drawLine(x, 0, x, gap)
            metrics = qp.fontMetrics()
            if pts % one_minute == 0:
                text = '{:02}:{:02}'.format(pts // one_minute, 0)
            elif pts % (10 * one_second) == 0:
                text = '{:02}'.format((pts % one_minute) // one_second)
            else:
                text = ''
            fw = metrics.width(text)
            fh = metrics.height()
            qp.drawText(x, gap + fh, text)

        qp.setPen(
            QtGui.QPen(self.palette().highlight(), 1, QtCore.Qt.SolidLine))
        last_line = None
        for i, line in enumerate(self._api.subtitles):
            qp.setBrush(QtGui.QBrush(
                self.palette().highlight().color(),
                QtCore.Qt.FDiagPattern if i & 1 else QtCore.Qt.BDiagPattern))
            x1 = self._pts_to_x(line.start)
            x2 = self._pts_to_x(line.end)
            qp.drawRect(x1, 30, x2 - x1, h - 30)

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
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()

    def drawWidget(self, qp):
        size = self.size()
        w = size.width()
        h = size.height()

        brush = QtGui.QBrush(self.palette().highlight())
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(brush)
        x1 = self._pts_to_x(self._api.audio.view_start)
        x2 = self._pts_to_x(self._api.audio.view_end)
        qp.drawRect(x1, 0, x2 - x1, h - 1)

        brush = QtGui.QBrush(self.palette().highlight())
        pen = QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine)
        qp.setPen(pen)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawRect(0, 0, w - 1, h - 1)

    def _pts_to_x(self, pts):
        scale = self.width() / max(1, self._api.audio.size)
        return (pts - self._api.audio.min) * scale


class Audio(QtWidgets.QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self._api = api
        self._audio_slider = AudioSliderWidget(self._api)
        self._audio_preview = AudioPreviewWidget(self._api)
        self._audio_preview.zoom[int].connect(self.on_audio_preview_zoom)
        self._audio_preview.scroll[int].connect(self.on_audio_preview_scroll)

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

    def on_audio_preview_zoom(self, delta):
        cur_factor = (
            (self._api.audio.view_end - self._api.audio.view_start) /
            (self._api.audio.max - self._api.audio.min))
        new_factor = cur_factor * (1.1 if delta < 0 else 0.9)
        self._api.audio.zoom(new_factor)
        self._repaint()

    def on_audio_preview_scroll(self, delta):
        distance = 1 if delta < 0 else -1
        distance *= self._api.audio.view_size * 0.05
        self._api.audio.move(distance)
        self._repaint()

    def _repaint(self):
        self._audio_slider.repaint()
        self._audio_preview.repaint()
