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

# X,Y to S,V mapping inside the triangle selector is taken
# from GTK2 color dialog and was written by Simon Budig.

import functools
import math
import sys
import typing as T

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.data import ROOT_DIR


@functools.lru_cache(1)
def _get_alpha_grid() -> QtGui.QPixmap:
    return QtGui.QPixmap(str(ROOT_DIR / "style_preview_bk" / "grid.png"))


def _black_or_white(color: QtGui.QColor) -> int:
    rgb: T.List[float] = []
    for c in [color.redF(), color.greenF(), color.blueF()]:
        if c <= 0.03928:
            c = c / 12.92
        else:
            c = ((c + 0.055) / 1.055) ** 2.4
        rgb.append(c)
    r, g, b = rgb
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if luminance > math.sqrt(1.05 * 0.05) - 0.05:
        return QtCore.Qt.black
    return QtCore.Qt.white


def _is_precise_click(
    button: QtCore.Qt.MouseButton, style: QtWidgets.QStyle
) -> bool:
    return (
        button & style.styleHint(QtWidgets.QStyle.SH_Slider_AbsoluteSetButtons)
    ) == button


def _is_imprecise_click(
    button: QtCore.Qt.MouseButton, style: QtWidgets.QStyle
) -> bool:
    return (
        button & style.styleHint(QtWidgets.QStyle.SH_Slider_PageSetButtons)
    ) == button


def _point_in_triangle(
    point: QtCore.QPoint,
    triangle_points: T.Tuple[QtCore.QPoint, QtCore.QPoint, QtCore.QPoint],
) -> bool:
    p = point
    p1, p2, p3 = triangle_points
    area = 0.5 * (
        -p2.y() * p3.x()
        + p1.y() * (-p2.x() + p3.x())
        + p1.x() * (p2.y() - p3.y())
        + p2.x() * p3.y()
    )
    s = (
        1
        / (2 * area)
        * (
            p1.y() * p3.x()
            - p1.x() * p3.y()
            + (p3.y() - p1.y()) * p.x()
            + (p1.x() - p3.x()) * p.y()
        )
    )
    t = (
        1
        / (2 * area)
        * (
            p1.x() * p2.y()
            - p1.y() * p2.x()
            + (p1.y() - p2.y()) * p.x()
            + (p2.x() - p1.x()) * p.y()
        )
    )
    return s > 0 and t > 0 and 1 - s - t > 0


def _point_in_ring(
    point: QtCore.QPoint, inner_radius: float, outer_radius: float
) -> bool:
    dist = (point.y() * point.y() + point.x() * point.x()) ** 0.5
    return inner_radius <= dist <= outer_radius


class ColorModel(QtCore.QObject):
    changed = QtCore.pyqtSignal()

    def __init__(self, color: QtGui.QColor) -> None:
        super().__init__()
        self._h: float = color.hueF()
        self._s: float = color.saturationF()
        self._v: float = color.valueF()
        self._r: float = color.redF()
        self._g: float = color.greenF()
        self._b: float = color.blueF()
        self._a: float = color.alphaF()
        self._syncing = False
        self._color = QtGui.QColor(color)

    @property
    def color(self) -> QtGui.QColor:
        return self._color

    @color.setter
    def color(self, color: QtGui.QColor) -> None:
        self._r = color.redF()
        self._g = color.greenF()
        self._b = color.greenF()
        self._sync_to_hsv()
        self.a = color.alphaF()

    def _sync_to_rgb(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        self._color = QtGui.QColor.fromHsvF(self.h, self.s, self.v, self.a)
        self.r = self._color.redF()
        self.g = self._color.greenF()
        self.b = self._color.blueF()
        self._syncing = False

    def _sync_to_hsv(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        self._color = QtGui.QColor.fromRgbF(self.r, self.g, self.b, self.a)
        self.h = self._color.hueF()
        self.s = self._color.saturationF()
        self.v = self._color.valueF()
        self._syncing = False

    @property
    def a(self) -> float:
        return self._a

    @a.setter
    def a(self, a: float) -> None:
        a = max(0.0, min(1.0, a))
        if a != self._a:
            self._a = a
            self.changed.emit()
            self._color.setAlphaF(a)

    @property
    def h(self) -> float:
        return self._h

    @h.setter
    def h(self, h: float) -> None:
        h = max(0.0, min(1.0, h))
        if h != self._h:
            self._h = h
            self._sync_to_rgb()
            self.changed.emit()

    @property
    def s(self) -> float:
        return self._s

    @s.setter
    def s(self, s: float) -> None:
        s = max(0.0, min(1.0, s))
        if s != self._s:
            self._s = s
            self._sync_to_rgb()
            self.changed.emit()

    @property
    def v(self) -> float:
        return self._v

    @v.setter
    def v(self, v: float) -> None:
        v = max(0.0, min(1.0, v))
        if v != self._v:
            self._v = v
            self._sync_to_rgb()
            self.changed.emit()

    @property
    def r(self) -> float:
        return self._r

    @r.setter
    def r(self, r: float) -> None:
        r = max(0.0, min(1.0, r))
        if r != self._r:
            self._r = r
            self._sync_to_hsv()
            self.changed.emit()

    @property
    def g(self) -> float:
        return self._g

    @g.setter
    def g(self, g: float) -> None:
        g = max(0.0, min(1.0, g))
        if g != self._g:
            self._g = g
            self._sync_to_hsv()
            self.changed.emit()

    @property
    def b(self) -> float:
        return self._b

    @b.setter
    def b(self, b: float) -> None:
        b = max(0.0, min(1.0, b))
        if b != self._b:
            self._b = b
            self._sync_to_hsv()
            self.changed.emit()


class ColorCircle(QtWidgets.QWidget):
    _ring_outer_radius = 150
    _ring_width = 35

    def __init__(self, parent: QtWidgets.QWidget, model: ColorModel) -> None:
        super().__init__(parent)
        self._model = model
        self._model.changed.connect(self.update)

        self._pressed_control: T.Optional[str] = None
        self._ring_gradient = QtGui.QConicalGradient(
            QtCore.QPoint(self._ring_outer_radius, self._ring_outer_radius),
            0.0,
        )
        self._ring_gradient.setColorAt(0 / 6, QtGui.QColor(255, 0, 0, 255))
        self._ring_gradient.setColorAt(1 / 6, QtGui.QColor(255, 0, 255, 255))
        self._ring_gradient.setColorAt(2 / 6, QtGui.QColor(0, 0, 255, 255))
        self._ring_gradient.setColorAt(3 / 6, QtGui.QColor(0, 255, 255, 255))
        self._ring_gradient.setColorAt(4 / 6, QtGui.QColor(0, 255, 0, 255))
        self._ring_gradient.setColorAt(5 / 6, QtGui.QColor(255, 255, 0, 255))
        self._ring_gradient.setColorAt(6 / 6, QtGui.QColor(255, 0, 0, 255))

        self.setFixedSize(self._ring_outer_diameter, self._ring_outer_diameter)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum
        )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self._draw_ring())
        painter.drawImage(0, 0, self._draw_triangle())

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        is_precise = _is_precise_click(event.button(), self.style())
        is_imprecise = _is_imprecise_click(event.button(), self.style())

        if is_precise or is_imprecise:
            if _point_in_ring(
                event.pos() - self.rect().center(),
                self._ring_inner_radius,
                self._ring_outer_radius,
            ):
                event.accept()
                self._sync_hue_from_ring(event.pos())
                if is_imprecise:
                    self._pressed_control = "ring"
                return

            if _point_in_triangle(event.pos(), self._get_triangle_points()):
                event.accept()
                self._sync_value_and_saturation_from_triangle(event.pos())
                if is_imprecise:
                    self._pressed_control = "triangle"
                return

        event.ignore()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._pressed_control == "ring":
            event.accept()
            self._sync_hue_from_ring(event.pos())
        elif self._pressed_control == "triangle":
            event.accept()
            self._sync_value_and_saturation_from_triangle(event.pos())
        else:
            event.ignore()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._pressed_control = None

    def _sync_value_and_saturation_from_triangle(
        self, pos: QtCore.QPoint
    ) -> None:
        p = pos
        p1, p2, p3 = self._get_triangle_points()

        center_x = self.rect().center().x()
        center_y = self.rect().center().y()

        x = pos.x() - center_x
        hx = p1.x() - center_x
        sx = p2.x() - center_x
        vx = p3.x() - center_x

        y = center_y - pos.y()
        hy = center_y - p1.y()
        sy = center_y - p2.y()
        vy = center_y - p3.y()

        if vx * (x - sx) + vy * (y - sy) < 0.0:
            self._model.s = 1.0
            self._model.v = ((x - sx) * (hx - sx) + (y - sy) * (hy - sy)) / (
                (hx - sx) * (hx - sx) + (hy - sy) * (hy - sy)
            )

        elif hx * (x - sx) + hy * (y - sy) < 0.0:
            self._model.s = 0.0
            self._model.v = ((x - sx) * (vx - sx) + (y - sy) * (vy - sy)) / (
                (vx - sx) * (vx - sx) + (vy - sy) * (vy - sy)
            )
        elif sx * (x - hx) + sy * (y - hy) < 0.0:
            self._model.v = 1.0
            self._model.s = ((x - vx) * (hx - vx) + (y - vy) * (hy - vy)) / (
                (hx - vx) * (hx - vx) + (hy - vy) * (hy - vy)
            )
        else:
            v = ((x - sx) * (hy - vy) - (y - sy) * (hx - vx)) / (
                (vx - sx) * (hy - vy) - (vy - sy) * (hx - vx)
            )

            if v <= 0.0:
                self._model.v = 0.0
                self._model.s = 0.0
            else:
                self._model.v = v

                if abs(hy - vy) < abs(hx - vx):
                    self._model.s = (x - sx - v * (vx - sx)) / (v * (hx - vx))
                else:
                    self._model.s = (y - sy - v * (vy - sy)) / (v * (hy - vy))

    def _sync_hue_from_ring(self, pos: QtCore.QPoint) -> None:
        pos -= self.rect().center()
        x = pos.x()
        y = pos.y()
        theta = (math.atan2(y, x) / (2 * math.pi)) % 1.0
        self._model.h = theta

    @property
    def _ring_inner_radius(self) -> int:
        return self._ring_outer_radius - self._ring_width

    @property
    def _ring_inner_diameter(self) -> int:
        return self._ring_inner_radius * 2

    @property
    def _ring_outer_diameter(self) -> int:
        return self._ring_outer_radius * 2

    @property
    def _triangle_side(self) -> int:
        return int(self._ring_inner_radius * 3 / math.sqrt(3))

    @property
    def _triangle_height(self) -> int:
        return int(self._ring_inner_radius * 3 / 2)

    def _get_triangle_transform(self) -> QtGui.QTransform:
        transform = QtGui.QTransform()
        transform.translate(self._ring_outer_radius, self._ring_outer_radius)
        transform.rotate(self._model.h * 360.0)
        transform.rotate(90.0)
        transform.translate(
            -self._triangle_side / 2, -self._triangle_height * 2 / 3
        )
        return transform

    def _get_triangle_points(
        self, use_transform: bool = True
    ) -> T.Tuple[QtCore.QPoint, QtCore.QPoint, QtCore.QPoint]:
        p1 = QtCore.QPoint(self._triangle_side / 2, 0)
        p2 = QtCore.QPoint(0, self._triangle_height)
        p3 = QtCore.QPoint(self._triangle_side, self._triangle_height)
        if use_transform:
            transform = self._get_triangle_transform()
            p1 = transform.map(p1)
            p2 = transform.map(p2)
            p3 = transform.map(p3)
        return (p1, p2, p3)

    def _draw_ring(self) -> QtGui.QImage:
        image = QtGui.QImage(
            self._ring_outer_diameter,
            self._ring_outer_diameter,
            QtGui.QImage.Format_ARGB32,
        )
        image.fill(0)

        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.white)
        painter.drawEllipse(
            0, 0, self._ring_outer_diameter, self._ring_outer_diameter
        )

        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
        painter.setBrush(QtCore.Qt.transparent)
        painter.drawEllipse(
            self._ring_width,
            self._ring_width,
            self._ring_inner_diameter,
            self._ring_inner_diameter,
        )

        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceAtop)
        painter.setBrush(QtGui.QBrush(self._ring_gradient))
        painter.drawRect(image.rect())

        theta = self._model.h
        painter.setPen(
            QtGui.QPen(
                _black_or_white(QtGui.QColor.fromHsvF(self._model.h, 1, 1)),
                1.5,
            )
        )
        painter.translate(self._ring_outer_radius, self._ring_outer_radius)
        painter.rotate(self._model.h * 360.0)
        painter.drawLine(0, 0, self._ring_outer_diameter, 0)

        return image

    def _draw_triangle(self) -> QtGui.QImage:
        height = self._triangle_height
        side = self._triangle_side

        image = QtGui.QImage(
            self._ring_outer_diameter,
            self._ring_outer_diameter,
            QtGui.QImage.Format_ARGB32,
        )
        image.fill(0)

        painter = QtGui.QPainter(image)
        painter.setRenderHint(painter.Antialiasing)

        p1, p2, p3 = self._get_triangle_points(use_transform=False)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.black)
        painter.setTransform(self._get_triangle_transform())
        painter.drawPolygon(p1, p2, p3)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceAtop)

        for y in range(0, height, 1):
            x1 = 0.5 - (y / height) / 2
            x2 = 1 - x1
            c1 = QtGui.QColor.fromHsvF(
                self._model.h, 1 - y / height, 1 - y / height
            )
            c2 = QtGui.QColor.fromHsvF(self._model.h, 1 - y / height, 1)

            gradient = QtGui.QLinearGradient(x1 * side, y, x2 * side, y)
            gradient.setColorAt(0, c1)
            gradient.setColorAt(1, c2)
            painter.setBrush(gradient)
            painter.drawRect(0, y, side, 2)

        v = self._model.v
        s = self._model.s
        cx = math.floor(
            p2.x() + (p3.x() - p2.x()) * v + (p1.x() - p3.x()) * s * v + 0.5
        )
        cy = math.floor(
            p2.y() + (p3.y() - p2.y()) * v + (p1.y() - p3.y()) * s * v + 0.5
        )

        painter.setPen(QtGui.QPen(_black_or_white(self._model.color), 1.5))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
        painter.drawEllipse(QtCore.QRect(cx - 5, cy - 5, 10, 10))

        return image


class ColorSlider(QtWidgets.QAbstractSlider):
    _thumb_size = 8

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        gradient_decorator: T.Callable[[QtGui.QLinearGradient], None],
        value: int,
    ) -> None:
        super().__init__(
            parent,
            minimum=0,
            maximum=255,
            orientation=QtCore.Qt.Horizontal,
            value=value,
        )
        self._gradient_decorator = gradient_decorator
        self._pressed_control = QtWidgets.QStyle.SC_None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum
        )

    def setValue(self, value: float) -> None:
        super().setValue(value)
        self.update()

    def sizeHint(self) -> T.Tuple[int, int]:
        return QtCore.QSize(300, 25)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        groove_rect = self._groove_rect
        handle_rect = self._handle_rect

        gradient = QtGui.QLinearGradient(
            groove_rect.topLeft(), groove_rect.topRight()
        )
        self._gradient_decorator(gradient)

        painter = QtGui.QPainter(self)
        painter.drawTiledPixmap(groove_rect, _get_alpha_grid())
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRect(groove_rect)

        opt = QtWidgets.QStyleOptionFrame()
        opt.rect = groove_rect
        opt.state = QtWidgets.QStyle.State_Sunken
        opt.lineWidth = 1
        opt.frameShape = QtWidgets.QFrame.Panel
        self.style().drawControl(
            QtWidgets.QStyle.CE_ShapedFrame, opt, painter, self
        )

        opt = QtWidgets.QStyleOptionButton()
        opt.state = (
            QtWidgets.QStyle.State_Active | QtWidgets.QStyle.State_Enabled
        )
        if self.isSliderDown():
            opt.state |= QtWidgets.QStyle.State_Sunken
        opt.rect = handle_rect
        self.style().drawControl(
            QtWidgets.QStyle.CE_PushButton, opt, painter, self
        )

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if _is_precise_click(event.button(), self.style()):
            event.accept()
            self.setSliderPosition(self._val_from_point(event.pos()))
            self.triggerAction(QtWidgets.QSlider.SliderMove)
            self._pressed_control = QtWidgets.QStyle.SC_SliderHandle
            self.update()

        elif _is_imprecise_click(event.button(), self.style()):
            event.accept()

            self._pressed_control = (
                QtWidgets.QStyle.SC_SliderHandle
                if event.pos() in self._handle_rect
                else QtWidgets.QStyle.SC_SliderGroove
            )

            action = self.SliderNoAction
            if self._pressed_control == QtWidgets.QStyle.SC_SliderGroove:
                press_value = self._val_from_point(event.pos())
                if press_value > self.value():
                    action = self.SliderPageStepAdd
                elif press_value < self.value():
                    action = self.SliderPageStepSub
                if action:
                    self.triggerAction(action)
                    self.setRepeatAction(action)

        else:
            event.ignore()
            return

        if self._pressed_control == QtWidgets.QStyle.SC_SliderHandle:
            self.setRepeatAction(self.SliderNoAction)
            self.update()
            self.setSliderDown(True)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._pressed_control != QtWidgets.QStyle.SC_SliderHandle:
            event.ignore()
            return
        event.accept()
        self.setSliderPosition(self._val_from_point(event.pos()))

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if (
            self._pressed_control == QtWidgets.QStyle.SC_None
            or event.buttons()
        ):
            event.ignore()
            return
        event.accept()
        old_pressed = QtWidgets.QStyle.SubControl(self._pressed_control)
        self._pressed_control = QtWidgets.QStyle.SC_None
        self.setRepeatAction(self.SliderNoAction)
        if old_pressed == QtWidgets.QStyle.SC_SliderHandle:
            self.setSliderDown(False)
        self.update()

    @property
    def _groove_rect(self) -> QtCore.QRect:
        return QtCore.QRect(
            self._thumb_size,
            3,
            self.width() - self._thumb_size * 2,
            self.height() - 6,
        )

    @property
    def _handle_rect(self) -> QtCore.QRect:
        x = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        x = x * (self.width() - self._thumb_size * 2)
        return QtCore.QRect(x, 0, self._thumb_size * 2, self.height())

    def _val_from_point(self, pos: QtCore.QPoint) -> int:
        center = self._handle_rect.center() - self._handle_rect.topLeft()
        x = (pos - center).x()
        return int(
            self.minimum()
            + x * (self.maximum() - self.minimum()) / self._groove_rect.width()
        )


class BaseColorControl(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget, model: ColorModel) -> None:
        super().__init__(parent)
        self._model = model

        self._slider = ColorSlider(
            self,
            gradient_decorator=lambda gradient: self._decorate_gradient(
                gradient, self._model.color
            ),
            value=int(self._get_value(self._model) * 255),
        )
        self._up_down = QtWidgets.QSpinBox(
            self,
            minimum=0,
            maximum=255,
            value=int(self._get_value(self._model) * 255),
        )

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._slider)
        layout.addWidget(self._up_down)

        self._slider.valueChanged.connect(self._slider_changed)
        self._up_down.valueChanged.connect(self._up_down_changed)
        self._model.changed.connect(self._model_changed)

    def _get_value(self, model: ColorModel) -> float:
        raise NotImplementedError("not implemented")

    def _set_value(self, model: ColorModel, value: float) -> None:
        raise NotImplementedError("not implemented")

    def _decorate_gradient(
        self, gradient: QtGui.QLinearGradient, color: QtGui.QColor
    ) -> None:
        tmp_model = ColorModel(self._model.color)
        tmp_model.a = 1.0
        self._set_value(tmp_model, 0.0)
        gradient.setColorAt(0, tmp_model.color)
        self._set_value(tmp_model, 1.0)
        gradient.setColorAt(1, tmp_model.color)

    def _model_changed(self) -> None:
        self._slider.setValue(self._get_value(self._model) * 255)
        self._up_down.setValue(self._get_value(self._model) * 255)

    def _slider_changed(self) -> None:
        self._set_value(self._model, self._slider.value() / 255.0)

    def _up_down_changed(self) -> None:
        self._set_value(self._model, self._up_down.value() / 255.0)


class HueColorControl(BaseColorControl):
    def _get_value(self, model: ColorModel) -> float:
        return model.h

    def _set_value(self, model: ColorModel, value: float) -> None:
        model.h = value

    def _decorate_gradient(
        self, gradient: QtGui.QLinearGradient, color: QtGui.QColor
    ) -> None:
        gradient.setColorAt(0 / 6, QtGui.QColor(255, 0, 0, 255))
        gradient.setColorAt(1 / 6, QtGui.QColor(255, 255, 0, 255))
        gradient.setColorAt(2 / 6, QtGui.QColor(0, 255, 0, 255))
        gradient.setColorAt(3 / 6, QtGui.QColor(0, 255, 255, 255))
        gradient.setColorAt(4 / 6, QtGui.QColor(0, 0, 255, 255))
        gradient.setColorAt(5 / 6, QtGui.QColor(255, 0, 255, 255))
        gradient.setColorAt(6 / 6, QtGui.QColor(255, 0, 0, 255))


class SaturationColorControl(BaseColorControl):
    def _get_value(self, model: ColorModel) -> float:
        return model.s

    def _set_value(self, model: ColorModel, value: float) -> None:
        model.s = value


class ValueColorControl(BaseColorControl):
    def _get_value(self, model: ColorModel) -> float:
        return model.v

    def _set_value(self, model: ColorModel, value: float) -> None:
        model.v = value


class RedColorControl(BaseColorControl):
    def _get_value(self, model: ColorModel) -> float:
        return model.r

    def _set_value(self, model: ColorModel, value: float) -> None:
        model.r = value


class GreenColorControl(BaseColorControl):
    def _get_value(self, model: ColorModel) -> float:
        return model.g

    def _set_value(self, model: ColorModel, value: float) -> None:
        model.g = value


class BlueColorControl(BaseColorControl):
    def _get_value(self, model: ColorModel) -> float:
        return model.b

    def _set_value(self, model: ColorModel, value: float) -> None:
        model.b = value


class AlphaColorControl(BaseColorControl):
    def _get_value(self, model: ColorModel) -> float:
        return model.a

    def _set_value(self, model: ColorModel, value: float) -> None:
        model.a = value

    def _decorate_gradient(
        self, gradient: QtGui.QLinearGradient, color: QtGui.QColor
    ) -> None:
        gradient.setColorAt(
            0, QtGui.QColor(color.red(), color.green(), color.blue(), 0)
        )
        gradient.setColorAt(
            1, QtGui.QColor(color.red(), color.green(), color.blue(), 255)
        )


class ColorPreview(QtWidgets.QFrame):
    def __init__(
        self,
        parent: QtWidgets.QWidget,
        orig_color: QtGui.QColor,
        model: ColorModel,
    ) -> None:
        super().__init__(parent)
        self._orig_color = orig_color
        self._model = model

        self.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)

        self._model.changed.connect(self.update)

    def sizeHint(self) -> T.Tuple[int, int]:
        return QtCore.QSize(300, 50)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        left = self.frameRect()
        left.setWidth(left.width() // 2)
        right = self.frameRect()
        right.setLeft(left.width())

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.drawTiledPixmap(self.frameRect(), _get_alpha_grid())
        self._draw_color(painter, left, self._orig_color)
        self._draw_color(painter, right, self._model.color)
        painter.end()

        super().paintEvent(event)

    def _draw_color(
        self, painter: QtGui.QPainter, rect: QtCore.QRect, color: QtGui.QColor
    ) -> None:
        text = f"#{color.red():02X}{color.green():02X}{color.blue():02X}"
        painter.fillRect(rect, color)

        painter.setPen(_black_or_white(color))
        painter.drawText(rect, QtCore.Qt.AlignCenter, text)

    def set_color(self, color: QtGui.QColor) -> None:
        self._color = color
        self.update()


class ColorDialog(QtWidgets.QDialog):
    def __init__(
        self,
        color: T.Optional[QtGui.QColor] = None,
        parent: QtWidgets.QWidget = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select color...")

        self._orig_color = color
        self._model = ColorModel(
            color if color is not None else QtGui.QColor(0, 0, 0)
        )

        strip = QtWidgets.QDialogButtonBox(self)
        strip.addButton(strip.Reset)
        strip.addButton(strip.Ok)
        strip.addButton(strip.Cancel)
        strip.accepted.connect(self.accept)
        strip.rejected.connect(self.reject)
        strip.button(strip.Reset).clicked.connect(self.reset)

        self._color_circle = ColorCircle(self, self._model)
        self._color_preview = ColorPreview(self, color, self._model)
        self._hue_slider = HueColorControl(self, self._model)
        self._saturation_slider = SaturationColorControl(self, self._model)
        self._value_slider = ValueColorControl(self, self._model)
        self._red_slider = RedColorControl(self, self._model)
        self._green_slider = GreenColorControl(self, self._model)
        self._blue_slider = BlueColorControl(self, self._model)
        self._alpha_slider = AlphaColorControl(self, self._model)

        circle_layout = QtWidgets.QVBoxLayout()
        circle_layout.setSpacing(16)
        circle_layout.setContentsMargins(0, 0, 16, 0)
        circle_layout.addWidget(self._color_circle)
        circle_layout.addWidget(self._color_preview)

        layout = QtWidgets.QGridLayout(self)

        layout.addLayout(circle_layout, 0, 0, 11, 1)
        layout.addWidget(QtWidgets.QLabel("Hue:", self), 0, 1)
        layout.addWidget(QtWidgets.QLabel("Saturation:", self), 1, 1)
        layout.addWidget(QtWidgets.QLabel("Value:", self), 2, 1)
        layout.addWidget(self._hue_slider, 0, 2)
        layout.addWidget(self._saturation_slider, 1, 2)
        layout.addWidget(self._value_slider, 2, 2)

        layout.addWidget(QtWidgets.QFrame(self), 3, 1, 1, 2)

        layout.addWidget(QtWidgets.QLabel("Red:", self), 4, 1)
        layout.addWidget(QtWidgets.QLabel("Green:", self), 5, 1)
        layout.addWidget(QtWidgets.QLabel("Blue:", self), 6, 1)
        layout.addWidget(self._red_slider, 4, 2)
        layout.addWidget(self._green_slider, 5, 2)
        layout.addWidget(self._blue_slider, 6, 2)

        layout.addWidget(QtWidgets.QFrame(self), 7, 1, 1, 2)

        layout.addWidget(QtWidgets.QLabel("Transparency:", self), 8, 1)
        layout.addWidget(self._alpha_slider, 8, 2)

        layout.addWidget(QtWidgets.QFrame(self), 9, 1, 1, 2)

        layout.addWidget(strip, 10, 1, 1, 2)

        self.show()

    def reset(self) -> None:
        self._model.color = self._orig_color

    def value(self) -> QtGui.QColor:
        return self._model.color
