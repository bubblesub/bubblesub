import enum
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui
from bubblesub.ui.util import blend_colors
from bubblesub.ui.spectrogram import SpectrumProvider, DERIVATION_SIZE


# TODO: draw position of video frame


class DragMode(enum.Enum):
    Off = 0
    SelectionStart = 1
    SelectionEnd = 2


class BaseAudioWidget(QtWidgets.QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self._api = api

        def upd(*_):
            self.update()

        api.audio.selection_changed.connect(upd)
        api.audio.view_changed.connect(upd)
        api.subs.lines.items_inserted.connect(upd)
        api.subs.lines.items_removed.connect(upd)
        api.subs.lines.item_changed.connect(upd)

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
            self._zoomed(event.angleDelta().y())
        else:
            self._scrolled(event.angleDelta().y())

    def _zoomed(self, delta):
        cur_factor = (
            (self._api.audio.view_end - self._api.audio.view_start) /
            (self._api.audio.max - self._api.audio.min))
        new_factor = cur_factor * (1.1 if delta < 0 else 0.9)
        self._api.audio.zoom_view(new_factor)

    def _scrolled(self, delta):
        distance = 1 if delta < 0 else -1
        distance *= self._api.audio.view_size * 0.05
        self._api.audio.move_view(distance)


class AudioScaleWidget(BaseAudioWidget):
    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self.setFixedHeight(20)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_scale(painter)
        self._draw_frame(painter)
        painter.end()

    def _draw_frame(self, painter):
        w, h = self.width(), self.height()
        painter.setPen(
            QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine))
        painter.drawLine(0, 0, w - 1, 0)
        painter.drawLine(0, 0, 0, h - 1)
        painter.drawLine(w - 1, 0, w - 1, h - 1)

    def _draw_scale(self, painter):
        w, h = self.width(), self.height()
        one_second = 1000
        one_minute = 60 * one_second

        start_pts = int(self._api.audio.view_start // one_minute) * one_minute
        end_pts = (
            (int(self._api.audio.view_end + one_minute) // one_minute)
            * one_minute)
        seconds_per_pixel = (
            (self._api.audio.view_end - self._api.audio.view_start)
            / self.width() / 1000.0)

        painter.setFont(QtGui.QFont(self.font().family(), 8))
        fh = painter.fontMetrics().capHeight()

        for pts in range(start_pts, end_pts, one_second):
            if pts % one_minute == 0:
                gap = self.height() - 1
            else:
                gap = 4

            x = self._pts_to_x(pts)
            painter.drawLine(x, 0, x, gap)
            if pts % one_minute == 0:
                text = '{:02}:{:02}'.format(pts // one_minute, 0)
            elif pts % (10 * one_second) == 0:
                text = '{:02}'.format((pts % one_minute) // one_second)
            else:
                text = ''
            painter.drawText(
                x + 2,
                fh + (self.height() - fh) / 2,
                text)

    def _pts_to_x(self, pts):
        scale = self.width() / max(1, self._api.audio.view_size)
        return (pts - self._api.audio.view_start) * scale


class AudioPreviewWidget(BaseAudioWidget):
    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self.setMinimumHeight(50)
        self.spectrum = None
        self._need_repaint = False
        self._drag_mode = DragMode.Off

        timer = QtCore.QTimer(self)
        timer.setInterval(100)
        timer.timeout.connect(self._repaint_if_needed)
        timer.start()

        api.video.loaded.connect(self._video_loaded)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_spectrogram(painter, event)
        painter.end()

        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_subtitle_rects(painter)
        self._draw_selection(painter)
        self._draw_frame(painter)
        painter.end()

        self._need_repaint = False

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_mode = DragMode.SelectionStart
            self.setCursor(QtCore.Qt.SizeHorCursor)
            self.mouseMoveEvent(event)
        elif event.button() == QtCore.Qt.RightButton:
            self._drag_mode = DragMode.SelectionEnd
            self.setCursor(QtCore.Qt.SizeHorCursor)
            self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_mode = DragMode.Off
        self.setCursor(QtCore.Qt.ArrowCursor)

    def mouseMoveEvent(self, event):
        pts = self._pts_from_x(event.x())
        if self._drag_mode == DragMode.SelectionStart:
            if self._api.audio.has_selection:
                self._api.audio.select(
                    min(self._api.audio.selection_end, pts),
                    self._api.audio.selection_end)
        elif self._drag_mode == DragMode.SelectionEnd:
            if self._api.audio.has_selection:
                self._api.audio.select(
                    self._api.audio.selection_start,
                    max(self._api.audio.selection_start, pts))

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

    def _draw_subtitle_rects(self, painter):
        w, h = self.width(), self.height()
        painter.setPen(
            QtGui.QPen(self.palette().highlight(), 1, QtCore.Qt.SolidLine))
        for i, line in enumerate(self._api.subs.lines):
            painter.setBrush(QtGui.QBrush(
                self.palette().highlight().color(),
                QtCore.Qt.FDiagPattern if i & 1 else QtCore.Qt.BDiagPattern))
            x1 = self._pts_to_x(line.start)
            x2 = self._pts_to_x(line.end)
            painter.drawRect(x1, 0, x2 - x1, h - 1)

    def _draw_selection(self, painter):
        if not self._api.audio.has_selection:
            return
        w, h = self.width(), self.height()
        if self.parent().hasFocus():
            color = QtGui.QColor(0xFF, 0xA0, 0x00)
        else:
            color = QtGui.QColor(0xA0, 0xA0, 0x60)
        painter.setPen(QtGui.QPen(color, 1, QtCore.Qt.SolidLine))
        color.setAlpha(0x40)
        painter.setBrush(QtGui.QBrush(color))
        x1 = self._pts_to_x(self._api.audio.selection_start)
        x2 = self._pts_to_x(self._api.audio.selection_end)
        painter.drawRect(x1, 0, x2 - x1, h - 1)

    def _draw_frame(self, painter):
        painter.setPen(
            QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

    def _pts_to_x(self, pts):
        scale = self.width() / max(1, self._api.audio.view_size)
        return (pts - self._api.audio.view_start) * scale

    def _pts_from_x(self, x):
        scale = self._api.audio.view_size / self.width()
        return x * scale + self._api.audio.view_start


class AudioSliderWidget(BaseAudioWidget):
    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self.setFixedHeight(20)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_slider(painter)
        self._draw_frame(painter)
        painter.end()

    def mousePressEvent(self, event):
        self.setCursor(QtCore.Qt.SizeHorCursor)
        self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(QtCore.Qt.ArrowCursor)

    def mouseMoveEvent(self, event):
        old_center = self._api.audio.view_start + self._api.audio.view_size / 2
        new_center = self._pts_from_x(event.x())
        distance = new_center - old_center
        self._api.audio.move_view(distance)

    def _draw_slider(self, painter):
        w, h = self.width(), self.height()
        brush = QtGui.QBrush(self.palette().highlight())
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(brush)
        x1 = self._pts_to_x(self._api.audio.view_start)
        x2 = self._pts_to_x(self._api.audio.view_end)
        painter.drawRect(x1, 0, x2 - x1, h - 1)

    def _draw_frame(self, painter):
        w, h = self.width(), self.height()
        painter.setPen(
            QtGui.QPen(self.palette().text(), 1, QtCore.Qt.SolidLine))
        painter.drawLine(0, 0, 0, h - 1)
        painter.drawLine(w - 1, 0, w - 1, h - 1)
        painter.drawLine(0, h - 1, w - 1, h - 1)

    def _pts_to_x(self, pts):
        scale = self.width() / max(1, self._api.audio.size)
        return (pts - self._api.audio.min) * scale

    def _pts_from_x(self, x):
        scale = self._api.audio.size / self.width()
        return x * scale + self._api.audio.min


class Audio(QtWidgets.QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self._api = api
        self._slider = AudioSliderWidget(self._api, self)
        self._scale = AudioScaleWidget(self._api, self)
        self._preview = AudioPreviewWidget(self._api, self)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(0)
        vbox.addWidget(self._scale)
        vbox.addWidget(self._preview)
        vbox.addWidget(self._slider)
        self.setLayout(vbox)

        api.subs.selection_changed.connect(self._grid_selection_changed)

    def _grid_selection_changed(self, rows):
        if len(rows) == 1:
            sub = self._api.subs.lines[rows[0]]
            self._api.audio.view(sub.start - 10000, sub.end + 10000)
            self._api.audio.select(sub.start, sub.end)
        else:
            self._api.audio.unselect()
