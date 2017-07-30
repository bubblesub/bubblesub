import enum
import numpy as np
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui
from bubblesub.ui.util import blend_colors
from bubblesub.ui.spectrogram import SpectrumProvider, DERIVATION_SIZE


NOT_CACHED = object()
CACHING = object()


class DragMode(enum.Enum):
    Off = 0
    SelectionStart = 1
    SelectionEnd = 2
    VideoPosition = 3


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

    def paintEvent(self, _event):
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
        h = self.height()
        one_second = 1000
        one_minute = 60 * one_second

        start_pts = int(self._api.audio.view_start // one_minute) * one_minute
        end_pts = (
            (int(self._api.audio.view_end + one_minute) // one_minute)
            * one_minute)

        painter.setFont(QtGui.QFont(self.font().family(), 8))
        text_height = painter.fontMetrics().capHeight()

        for pts in range(start_pts, end_pts, one_second):
            if pts % one_minute == 0:
                gap = h - 1
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
                text_height + (h - text_height) / 2,
                text)

    def _pts_to_x(self, pts):
        scale = self.width() / max(1, self._api.audio.view_size)
        return (pts - self._api.audio.view_start) * scale


class AudioPreviewWidget(BaseAudioWidget):
    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self.setMinimumHeight(50)
        self._spectrum_provider = SpectrumProvider(self, self._api)
        self._spectrum_provider.finished.connect(self._spectrum_updated)
        self._spectrum_cache = {}
        self._need_repaint = False
        self._drag_mode = DragMode.Off

        self._color_table = []
        for i in range(256):
            self._color_table.append(
                blend_colors(
                    self.palette().window().color(),
                    self.palette().text().color(),
                    i / 255))

        timer = QtCore.QTimer(
            self,
            interval=api.opt.general['audio']['spectrogram_sync_interval'])
        timer.timeout.connect(self._repaint_if_needed)
        timer.start()

        api.video.pos_changed.connect(self._video_pos_changed)
        api.video.loaded.connect(self._video_loaded)

    def paintEvent(self, _event):
        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_spectrogram(painter, _event)
        painter.end()

        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_subtitle_rects(painter)
        self._draw_selection(painter)
        self._draw_frame(painter)
        self._draw_video_pos(painter)
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
        elif event.button() == QtCore.Qt.MiddleButton:
            self._drag_mode = DragMode.VideoPosition
            self.setCursor(QtCore.Qt.SizeHorCursor)
            self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, _event):
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
        elif self._drag_mode == DragMode.VideoPosition:
            self._api.video.seek(pts)

    def _repaint_if_needed(self):
        if self._need_repaint:
            self.update()

    def _video_loaded(self):
        self._spectrum_cache.clear()
        self.update()

    def _video_pos_changed(self):
        self._need_repaint = True

    def _spectrum_updated(self, result):
        pts, column = result
        self._spectrum_cache[pts] = column
        self._need_repaint = True

    def _draw_spectrogram(self, painter, _event):
        width = self.width()
        height = (1 << DERIVATION_SIZE) + 1

        pixels = np.zeros([width, height], dtype='byte')
        horizontal_res = (
            self._api.opt.general['audio']['spectrogram_resolution'])

        # since the task queue is a LIFO queue, in order to render the columns
        # left-to-right, they need to be iterated backwards (hence reversed()).
        for x in reversed(range(self.width())):
            pts = self._pts_from_x(x)
            pts = (pts // horizontal_res) * horizontal_res
            column = self._spectrum_cache.get(pts, NOT_CACHED)
            if column is NOT_CACHED:
                self._spectrum_provider.schedule(pts)
                self._spectrum_cache[pts] = CACHING
                continue
            if column is CACHING:
                continue
            pixels[x] = column

        pixels = pixels.transpose().copy()
        image = QtGui.QImage(
            pixels.data,
            pixels.shape[1],
            pixels.shape[0],
            pixels.strides[0],
            QtGui.QImage.Format_Indexed8)
        image.setColorTable(self._color_table)
        painter.scale(1, self.height() / (height - 1))
        painter.drawPixmap(0, 0, QtGui.QPixmap.fromImage(image))

    def _draw_subtitle_rects(self, painter):
        h = self.height()
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
        h = self.height()
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

    def _draw_video_pos(self, painter):
        if not self._api.video.current_pts:
            return
        base_x = self._pts_to_x(self._api.video.current_pts)
        width = 4
        for dist in range(width):
            x = base_x + 1 - dist
            painter.setPen(
                QtGui.QPen(
                    QtGui.QColor(0, 160, 0, 255 - dist * 255 / width),
                    1, QtCore.Qt.SolidLine))
            painter.drawLine(x, 0, x, self.height() - 1)

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

    def paintEvent(self, _event):
        painter = QtGui.QPainter()
        painter.begin(self)
        self._draw_subtitle_rects(painter)
        self._draw_slider(painter)
        self._draw_frame(painter)
        painter.end()

    def mousePressEvent(self, event):
        self.setCursor(QtCore.Qt.SizeHorCursor)
        self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, _event):
        self.setCursor(QtCore.Qt.ArrowCursor)

    def mouseMoveEvent(self, event):
        old_center = self._api.audio.view_start + self._api.audio.view_size / 2
        new_center = self._pts_from_x(event.x())
        distance = new_center - old_center
        self._api.audio.move_view(distance)

    def _draw_subtitle_rects(self, painter):
        h = self.height()
        painter.setPen(QtCore.Qt.NoPen)
        color = self.palette().highlight().color()
        color.setAlpha(40)
        painter.setBrush(QtGui.QBrush(color))
        for line in self._api.subs.lines:
            x1 = self._pts_to_x(line.start)
            x2 = self._pts_to_x(line.end)
            painter.drawRect(x1, 0, x2 - x1, h - 1)

    def _draw_slider(self, painter):
        h = self.height()
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

        self.setLayout(QtWidgets.QVBoxLayout(self))
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._scale)
        self.layout().addWidget(self._preview)
        self.layout().addWidget(self._slider)

        api.subs.selection_changed.connect(self._grid_selection_changed)

    def _grid_selection_changed(self, rows):
        if len(rows) == 1:
            sub = self._api.subs.lines[rows[0]]
            self._api.audio.view(sub.start - 10000, sub.end + 10000)
            self._api.audio.select(sub.start, sub.end)
        else:
            self._api.audio.unselect()
