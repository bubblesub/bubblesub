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
import fractions
import re
import typing as T
from math import floor

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.playback import (
    MAX_PLAYBACK_SPEED,
    MAX_VOLUME,
    MIN_PLAYBACK_SPEED,
    MIN_VOLUME,
)
from bubblesub.ui.mpv import MpvWidget
from bubblesub.ui.util import get_icon
from bubblesub.util import all_subclasses

EPSILON = 1e-7
LOCK_X_AXIS_MODIFIER = QtCore.Qt.ShiftModifier
LOCK_Y_AXIS_MODIFIER = QtCore.Qt.ControlModifier
PAN_X_MODIFIER = LOCK_Y_AXIS_MODIFIER
PAN_Y_MODIFIER = LOCK_X_AXIS_MODIFIER


def clean_ass_tags(text: str) -> str:
    text = text.replace("}{", "")
    text = text.replace("{}", "")
    return text


class VideoInteractionMode(enum.IntEnum):
    Zoom = 1
    Pan = 2
    SubPosition = 3
    SubRotation = 4
    SubRotationOrigin = 5
    SubShear = 6
    SubScale = 7


class MousePosCalculator:
    def __init__(self, api: Api) -> None:
        self._api = api
        self.display_width = 1
        self.display_height = 1

    def get_display_pos(self, event: QtGui.QMouseEvent) -> QtCore.QPointF:
        return QtCore.QPointF(
            event.pos().x() / self.display_width,
            event.pos().y() / self.display_height,
        )

    def get_video_pos(
        self, event: QtGui.QMouseEvent
    ) -> T.Optional[QtCore.QPointF]:
        if not self._api.video.current_stream:
            return None

        zoom = self._api.video.view.zoom
        pan_x = self._api.video.view.pan_x
        pan_y = self._api.video.view.pan_y

        display_w = self.display_width
        display_h = self.display_height
        display_ar = display_w / display_h
        video_w = self._api.video.current_stream.width
        video_h = self._api.video.current_stream.height
        video_ar = video_w / video_h

        if display_ar > video_ar:
            scale = display_h / video_h
        else:
            scale = display_w / video_w

        # coordinates of the video frame
        scaled_video_w = video_w * scale
        scaled_video_h = video_h * scale
        scaled_video_w *= 2 ** zoom
        scaled_video_h *= 2 ** zoom
        scaled_video_x = (display_w - scaled_video_w) / 2
        scaled_video_y = (display_h - scaled_video_h) / 2
        scaled_video_x += pan_x * scaled_video_w
        scaled_video_y += pan_y * scaled_video_h

        if scaled_video_w < EPSILON or scaled_video_h < EPSILON:
            return None

        return QtCore.QPointF(
            (event.pos().x() - scaled_video_x) * video_w / scaled_video_w,
            (event.pos().y() - scaled_video_y) * video_h / scaled_video_h,
        )


class VideoMouseHandler:
    mode: VideoInteractionMode = NotImplemented

    def __init__(self, api: Api, mouse_pos_calc: MousePosCalculator) -> None:
        self._api = api
        self._mouse_pos_calc = mouse_pos_calc

    def on_drag_start(self, event: QtGui.QMouseEvent) -> None:
        pass

    def on_drag_move(self, event: QtGui.QMouseEvent) -> None:
        pass

    def on_drag_release(self, event: QtGui.QMouseEvent) -> None:
        pass

    def on_middle_click(self, event: QtGui.QMouseEvent) -> None:
        pass


class AbsolutePositionVideoMouseHandler(VideoMouseHandler):
    def on_drag_start(self, event: QtGui.QMouseEvent) -> None:
        self._api.undo.begin_capture()

    def on_drag_release(self, event: QtGui.QMouseEvent) -> None:
        self._api.undo.end_capture()

    def on_drag_move(self, event: QtGui.QMouseEvent) -> None:
        sel = self._api.subs.selected_events
        video_pos = self._mouse_pos_calc.get_video_pos(event)
        if not sel or not video_pos:
            return
        for sub in sel:
            text = sub.text

            match = self._get_regex().search(text)
            sub_x = float(match.group("x")) if match else 0.0
            sub_y = float(match.group("y")) if match else 0.0
            new_x = video_pos.x()
            new_y = video_pos.y()
            if event.modifiers() & LOCK_X_AXIS_MODIFIER:
                new_x = sub_x
            elif event.modifiers() & LOCK_Y_AXIS_MODIFIER:
                new_y = sub_y

            text = self._get_regex().sub("", text)
            text = self._get_ass_tag(new_x, new_y) + text
            text = clean_ass_tags(text)
            sub.text = text

    def on_middle_click(self, event: QtGui.QMouseEvent) -> None:
        with self._api.undo.capture():
            for sub in self._api.subs.selected_events:
                sub.text = clean_ass_tags(self._get_regex().sub("", sub.text))

    def _get_ass_tag(self, x: float, y: float) -> str:
        raise NotImplementedError("not implemented")

    def _get_regex(self) -> T.Pattern:
        raise NotImplementedError("not implemented")


class RelativeAxisVideoMouseHandler(VideoMouseHandler):
    default_scale = 1.0
    default_initial_value_x = 0.0
    default_initial_value_y = 0.0

    def __init__(self, api: Api, mouse_pos_calc: MousePosCalculator) -> None:
        super().__init__(api, mouse_pos_calc)
        self._initial_value_x = self.default_initial_value_x
        self._initial_value_y = self.default_initial_value_y
        self._initial_display_pos = QtCore.QPointF(0, 0)

    def on_drag_start(self, event: QtGui.QMouseEvent) -> None:
        self._api.undo.begin_capture()

        self._initial_value_x = self.default_initial_value_x
        self._initial_value_y = self.default_initial_value_y
        sel = self._api.subs.selected_events
        if sel:
            match = self._get_regex("x").search(sel[0].text)
            if match:
                self._initial_value_x = float(match.group("value"))
            match = self._get_regex("y").search(sel[0].text)
            if match:
                self._initial_value_y = float(match.group("value"))

        self._initial_display_pos = self._mouse_pos_calc.get_display_pos(event)

    def on_drag_release(self, event: QtGui.QMouseEvent) -> None:
        self._api.undo.end_capture()

    def on_drag_move(self, event: QtGui.QMouseEvent) -> None:
        sel = self._api.subs.selected_events
        if not sel:
            return
        display_pos = self._mouse_pos_calc.get_display_pos(event)
        value_x = self._initial_value_x + (
            display_pos.x() - self._initial_display_pos.x()
        ) * 2 * self.default_scale / (
            self.default_scale ** self._api.video.view.zoom
        )
        value_y = self._initial_value_y + (
            display_pos.y() - self._initial_display_pos.y()
        ) * 2 * self.default_scale / (
            self.default_scale ** self._api.video.view.zoom
        )

        for sub in sel:
            text = sub.text
            if not event.modifiers() & LOCK_X_AXIS_MODIFIER:
                text = self._get_regex("x").sub("", text)
                text = self._get_ass_tag("x", value_x) + text
            if not event.modifiers() & LOCK_Y_AXIS_MODIFIER:
                text = self._get_regex("y").sub("", text)
                text = self._get_ass_tag("y", value_y) + text
            text = clean_ass_tags(text)
            sub.text = text

    def on_middle_click(self, event: QtGui.QMouseEvent) -> None:
        with self._api.undo.capture():
            for sub in self._api.subs.selected_events:
                text = sub.text
                text = self._get_regex("x").sub("", text)
                text = self._get_regex("y").sub("", text)
                text = clean_ass_tags(text)
                sub.text = text

    def _get_ass_tag(self, axis: str, value: float) -> str:
        raise NotImplementedError("not implemented")

    def _get_regex(self, axis: str) -> T.Pattern:
        raise NotImplementedError("not implemented")


class ZoomVideoMouseHandler(VideoMouseHandler):
    mode = VideoInteractionMode.Zoom

    def __init__(self, api: Api, mouse_pos_calc: MousePosCalculator) -> None:
        super().__init__(api, mouse_pos_calc)
        self._initial_zoom = 0.0
        self._initial_display_pos = QtCore.QPointF(0, 0)

    def on_drag_start(self, event: QtGui.QMouseEvent) -> None:
        self._initial_zoom = self._api.video.view.zoom
        self._initial_display_pos = self._mouse_pos_calc.get_display_pos(event)

    def on_drag_move(self, event: QtGui.QMouseEvent) -> None:
        display_pos = self._mouse_pos_calc.get_display_pos(event)
        self._api.video.view.zoom = (
            self._initial_zoom
            + display_pos.x()
            - self._initial_display_pos.x()
        )

    def on_middle_click(self, event: QtGui.QMouseEvent) -> None:
        self._api.video.view.zoom = fractions.Fraction(0, 1)


class PanVideoMouseHandler(VideoMouseHandler):
    mode = VideoInteractionMode.Pan

    def __init__(self, api: Api, mouse_pos_calc: MousePosCalculator) -> None:
        super().__init__(api, mouse_pos_calc)
        self._initial_pan_x = 0.0
        self._initial_pan_y = 0.0
        self._initial_display_pos = QtCore.QPointF(0, 0)

    def on_drag_start(self, event: QtGui.QMouseEvent) -> None:
        self._initial_pan_x = self._api.video.view.pan_x
        self._initial_pan_y = self._api.video.view.pan_y
        self._initial_display_pos = self._mouse_pos_calc.get_display_pos(event)

    def on_drag_move(self, event: QtGui.QMouseEvent) -> None:
        display_pos = self._mouse_pos_calc.get_display_pos(event)
        self._api.video.view.pan_x = self._initial_pan_x + (
            display_pos.x() - self._initial_display_pos.x()
        ) / (2 ** self._api.video.view.zoom)
        self._api.video.view.pan_y = self._initial_pan_y + (
            display_pos.y() - self._initial_display_pos.y()
        ) / (2 ** self._api.video.view.zoom)

    def on_middle_click(self, event: QtGui.QMouseEvent) -> None:
        self._api.video.view.pan = (
            fractions.Fraction(0, 1),
            fractions.Fraction(0, 1),
        )


class SubPositionVideoMouseHandler(AbsolutePositionVideoMouseHandler):
    mode = VideoInteractionMode.SubPosition

    def _get_ass_tag(self, x: float, y: float) -> str:
        return f"{{\\pos({x:.2f},{y:.2f})}}"

    def _get_regex(self) -> T.Pattern:
        return re.compile(r"\\pos\((?P<x>-?[0-9\.]+),(?P<y>-?[0-9\.]+)\)")


class SubRotationHandler(VideoMouseHandler):
    mode = VideoInteractionMode.SubRotation

    def __init__(self, api: Api, mouse_pos_calc: MousePosCalculator) -> None:
        super().__init__(api, mouse_pos_calc)
        self._initial_angle = 0.0
        self._initial_display_pos = QtCore.QPointF(0, 0)

    def on_drag_start(self, event: QtGui.QMouseEvent) -> None:
        self._api.undo.begin_capture()

        self._initial_angle = 0.0
        sel = self._api.subs.selected_events
        if sel:
            axis = self._get_axis(event)
            match = self._get_regex(axis).search(sel[0].text)
            if match:
                self._initial_angle = float(match.group("value"))

        self._initial_display_pos = self._mouse_pos_calc.get_display_pos(event)

    def on_drag_release(self, event: QtGui.QMouseEvent) -> None:
        self._api.undo.end_capture()

    def on_drag_move(self, event: QtGui.QMouseEvent) -> None:
        sel = self._api.subs.selected_events
        if not sel:
            return
        axis = self._get_axis(event)
        display_pos = self._mouse_pos_calc.get_display_pos(event)
        angle = self._initial_angle + (
            display_pos.x() - self._initial_display_pos.x()
        ) * 360 / (2 ** self._api.video.view.zoom)
        for sub in sel:
            text = sub.text
            text = self._get_regex(axis).sub("", text)
            text = f"{{\\fr{axis}{angle:.1f}}}" + text
            text = clean_ass_tags(text)
            sub.text = text

    def on_middle_click(self, event: QtGui.QMouseEvent) -> None:
        axis = self._get_axis(event)
        with self._api.undo.capture():
            for sub in self._api.subs.selected_events:
                sub.text = clean_ass_tags(
                    self._get_regex(axis).sub("", sub.text)
                )

    def _get_axis(self, event: QtGui.QMouseEvent) -> str:
        if event.modifiers() & QtCore.Qt.ShiftModifier:
            return "y"
        if event.modifiers() & QtCore.Qt.ControlModifier:
            return "x"
        return "z"

    def _get_regex(self, axis: str) -> T.Pattern:
        return re.compile(rf"\\fr{axis}(?P<value>-?[0-9\.]+)")


class SubRotationOriginVideoMouseHandler(AbsolutePositionVideoMouseHandler):
    mode = VideoInteractionMode.SubRotationOrigin

    def _get_ass_tag(self, x: float, y: float) -> str:
        return f"{{\\org({x:.2f},{y:.2f})}}"

    def _get_regex(self) -> T.Pattern:
        return re.compile(r"\\org\((?P<x>-?[0-9\.]+),(?P<y>-?[0-9\.]+)\)")


class SubShearVideoMouseHandler(RelativeAxisVideoMouseHandler):
    mode = VideoInteractionMode.SubShear
    default_scale = 2.0

    def _get_ass_tag(self, axis: str, value: float) -> str:
        return f"{{\\fa{axis}{value:.2f}}}"

    def _get_regex(self, axis: str) -> T.Pattern:
        return re.compile(rf"\\fa{axis}(?P<value>-?[0-9\.]+)")


class SubScaleVideoMouseHandler(RelativeAxisVideoMouseHandler):
    mode = VideoInteractionMode.SubScale
    default_scale = 100.0
    default_initial_value_x = 100.0
    default_initial_value_y = 100.0

    def _get_ass_tag(self, axis: str, value: float) -> str:
        return f"{{\\fsc{axis}{value:.2f}}}"

    def _get_regex(self, axis: str) -> T.Pattern:
        return re.compile(rf"\\fsc{axis}(?P<value>-?[0-9\.]+)")


class VideoMouseModeController(QtCore.QObject):
    mode_changed = QtCore.pyqtSignal(object)

    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.mouse_pos_calc = MousePosCalculator(api)
        self._api = api

        self._dragging: T.Optional[QtCore.Qt.MouseButton] = None
        self._mode: T.Optional[VideoInteractionMode] = None
        self._handlers = {
            cls.mode: cls(api, self.mouse_pos_calc)
            for cls in all_subclasses(VideoMouseHandler)
            if cls.mode is not NotImplemented
        }

    @property
    def mode(self) -> T.Optional[VideoInteractionMode]:
        return self._mode

    @mode.setter
    def mode(self, value: T.Optional[VideoInteractionMode]):
        if value != self._mode:
            self._mode = value
            self.mode_changed.emit(self._mode)

    @property
    def current_handler(self) -> T.Optional[VideoMouseHandler]:
        return None if self._mode is None else self._handlers[self._mode]

    def on_wheel_turn(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & PAN_X_MODIFIER:
            self._api.video.view.pan_x += event.angleDelta().y() / 15 / 100
        elif event.modifiers() & PAN_Y_MODIFIER:
            self._api.video.view.pan_y += event.angleDelta().y() / 15 / 100
        else:
            self._api.video.view.zoom += event.angleDelta().y() / 15 / 100

    def on_mouse_press(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MiddleButton:
            if self.current_handler:
                self.current_handler.on_middle_click(event)
            return
        self._dragging = event.button()
        if event.button() == QtCore.Qt.LeftButton and self.current_handler:
            self.current_handler.on_drag_start(event)
            self.current_handler.on_drag_move(event)
        if event.button() == QtCore.Qt.RightButton:
            self._handlers[VideoInteractionMode.Pan].on_drag_start(event)
            self._handlers[VideoInteractionMode.Pan].on_drag_move(event)

    def on_mouse_move(self, event: QtGui.QMouseEvent) -> None:
        if self._dragging == QtCore.Qt.LeftButton and self.current_handler:
            self.current_handler.on_drag_move(event)
        if self._dragging == QtCore.Qt.RightButton:
            self._handlers[VideoInteractionMode.Pan].on_drag_move(event)

    def on_mouse_release(self, event: QtGui.QMouseEvent) -> None:
        if self._dragging == QtCore.Qt.LeftButton and self.current_handler:
            self.current_handler.on_drag_release(event)
        if self._dragging == QtCore.Qt.RightButton:
            self._handlers[VideoInteractionMode.Pan].on_drag_release(event)
        self._dragging = None


class VideoPreview(MpvWidget):
    def __init__(
        self,
        api: Api,
        controller: VideoMouseModeController,
        parent: QtWidgets.QWidget,
    ) -> None:
        super().__init__(api, parent)
        self._controller = controller
        self._controller.mode_changed.connect(self._on_mode_change)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400, 300)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        self._controller.on_wheel_turn(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._controller.on_mouse_press(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        self._controller.on_mouse_move(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._controller.on_mouse_release(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._controller.mouse_pos_calc.display_width = self.width()
        self._controller.mouse_pos_calc.display_height = self.height()
        super().resizeEvent(event)

    def _on_mode_change(self, mode: T.Optional[VideoInteractionMode]) -> None:
        self.setCursor(
            QtCore.Qt.ArrowCursor if mode is None else QtCore.Qt.CrossCursor
        )


class VideoModeButtons(QtWidgets.QToolBar):
    def __init__(
        self,
        api: Api,
        controller: VideoMouseModeController,
        parent: QtWidgets.QWidget,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._controller = controller

        self.setOrientation(QtCore.Qt.Vertical)
        self.setObjectName("video-controller")

        self._btn_group = QtWidgets.QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._btn_group.buttonToggled.connect(self._on_mode_btn_toggle)

        self._add_action_btn(
            "reset", "Reset video view", self._on_reset_btn_click
        )
        self._add_mode_btn("zoom-in", "Zoom video", VideoInteractionMode.Zoom)
        self._add_mode_btn("move", "Pan video", VideoInteractionMode.Pan)

        self.addSeparator()

        self._add_mode_btn(
            "sub-position",
            "Move selected subtitles",
            VideoInteractionMode.SubPosition,
        )
        self._add_mode_btn(
            "sub-rotation",
            "Rotate selected subtitles",
            VideoInteractionMode.SubRotation,
        )
        self._add_mode_btn(
            "sub-rotation-origin",
            "Set rotation origin for selected subtitles",
            VideoInteractionMode.SubRotationOrigin,
        )
        self._add_mode_btn(
            "sub-shear",
            "Shear selected subtitles",
            VideoInteractionMode.SubShear,
        )
        self._add_mode_btn(
            "sub-scale",
            "Scale selected subtitles",
            VideoInteractionMode.SubScale,
        )

    def _add_action_btn(
        self, icon_name: str, tooltip: str, callback: T.Callable[[], T.Any]
    ) -> None:
        btn = QtWidgets.QToolButton(self)
        btn.setToolTip(tooltip)
        btn.setIcon(get_icon(icon_name))
        btn.pressed.connect(self._reset_mode)
        btn.pressed.connect(callback)
        self.addWidget(btn)

    def _add_mode_btn(
        self, icon_name: str, tooltip: str, mode: VideoInteractionMode
    ) -> None:
        btn = QtWidgets.QToolButton(self)
        btn.setToolTip(tooltip)
        btn.setIcon(get_icon(icon_name))
        btn.setProperty("mode", mode)
        btn.setCheckable(True)
        btn.pressed.connect(self._on_mode_btn_press)
        btn.released.connect(self._on_mode_btn_release)
        self.addWidget(btn)
        self._btn_group.addButton(btn)

    def _on_mode_btn_press(self):
        btn = self.sender()
        checked_btn = self._btn_group.checkedButton()
        if checked_btn is not None and checked_btn == btn:
            self._btn_group.setExclusive(False)

    def _on_mode_btn_release(self):
        btn = self.sender()
        if self._btn_group.exclusive() is False:
            btn.setChecked(False)
            self._btn_group.setExclusive(True)

    def _on_mode_btn_toggle(
        self, btn: QtWidgets.QToolButton, checked: bool
    ) -> None:
        if checked:
            mode: VideoInteractionMode = btn.property("mode")
            self._controller.mode = mode
        else:
            self._controller.mode = None

    def _reset_mode(self) -> None:
        btn = self._btn_group.button(self._btn_group.checkedId())
        if btn is not None:
            self._btn_group.setExclusive(False)
            btn.setChecked(False)
            self._btn_group.setExclusive(True)

    def _on_reset_btn_click(self) -> None:
        self._api.video.view.zoom = fractions.Fraction(0, 1)
        self._api.video.view.pan = (
            fractions.Fraction(0, 1),
            fractions.Fraction(0, 1),
        )


class VideoPlaybackButtons(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._api = api

        self._play_pause_btn = QtWidgets.QPushButton("Play", self)
        self._play_pause_btn.setIcon(get_icon("play"))
        self._play_pause_btn.setCheckable(True)

        self._sync_video_pos_checkbox = QtWidgets.QCheckBox(
            "Seek to selected subtitles", self
        )
        self._sync_video_pos_checkbox.setChecked(
            self._api.cfg.opt["video"]["sync_pos_to_selection"]
        )

        self._playback_speed_spinbox = QtWidgets.QDoubleSpinBox()
        self._playback_speed_spinbox.setMinimum(float(MIN_PLAYBACK_SPEED))
        self._playback_speed_spinbox.setMaximum(float(MAX_PLAYBACK_SPEED))
        self._playback_speed_spinbox.setSingleStep(0.1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._play_pause_btn)
        layout.addStretch()
        layout.addWidget(self._sync_video_pos_checkbox)
        layout.addWidget(QtWidgets.QLabel("Playback speed:", self))
        layout.addWidget(self._playback_speed_spinbox)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum
        )

        self._connect_ui_signals()

        self._api.playback.pause_changed.connect(self._on_video_pause_change)
        self._api.playback.playback_speed_changed.connect(
            self._on_video_playback_speed_change
        )

        self._on_video_pause_change()
        self._on_video_playback_speed_change()

    def _connect_ui_signals(self) -> None:
        self._play_pause_btn.toggled.connect(self._on_play_pause_btn_toggle)
        self._playback_speed_spinbox.valueChanged.connect(
            self._on_playback_speed_spinbox_change
        )
        self._sync_video_pos_checkbox.clicked.connect(
            self._on_sync_video_pos_checkbox_click
        )

    def _disconnect_ui_signals(self) -> None:
        self._play_pause_btn.toggled.disconnect(self._on_play_pause_btn_toggle)
        self._playback_speed_spinbox.valueChanged.disconnect(
            self._on_playback_speed_spinbox_change
        )
        self._sync_video_pos_checkbox.clicked.disconnect(
            self._on_sync_video_pos_checkbox_click
        )

    def _on_play_pause_btn_toggle(self, checked: bool) -> None:
        self._api.playback.is_paused = not checked
        self._on_video_pause_change()

    def _on_playback_speed_spinbox_change(self) -> None:
        self._api.playback.playback_speed = (
            self._playback_speed_spinbox.value()
        )
        self._on_video_playback_speed_change()

    def _on_video_pause_change(self) -> None:
        self._disconnect_ui_signals()
        self._play_pause_btn.setChecked(not self._api.playback.is_paused)
        self._play_pause_btn.setText(
            "Paused" if self._api.playback.is_paused else "Playing"
        )
        self._play_pause_btn.setIcon(
            get_icon("pause" if self._api.playback.is_paused else "play")
        )
        self._connect_ui_signals()

    def _on_video_playback_speed_change(self) -> None:
        self._disconnect_ui_signals()
        self._playback_speed_spinbox.setValue(
            self._api.playback.playback_speed
        )
        self._connect_ui_signals()

    def _on_sync_video_pos_checkbox_click(self) -> None:
        self._api.cfg.opt["video"][
            "sync_pos_to_selection"
        ] = self._sync_video_pos_checkbox.isChecked()


class VideoVolumeControl(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._api = api

        self._volume_slider = QtWidgets.QSlider(self)
        self._volume_slider.setMinimum(float(MIN_VOLUME))
        self._volume_slider.setMaximum(float(MAX_VOLUME))
        self._volume_slider.setToolTip("Volume")

        self._mute_btn = QtWidgets.QPushButton(self)
        self._mute_btn.setCheckable(True)
        self._mute_btn.setToolTip("Mute")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._volume_slider)
        layout.addWidget(self._mute_btn)
        layout.setAlignment(self._volume_slider, QtCore.Qt.AlignHCenter)

        self.setObjectName("video-volume")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum
        )

        self._connect_ui_signals()

        self._api.playback.volume_changed.connect(self._on_video_volume_change)
        self._api.playback.mute_changed.connect(self._on_video_mute_change)

        self._on_video_volume_change()
        self._on_video_mute_change()

    def _connect_ui_signals(self) -> None:
        self._volume_slider.valueChanged.connect(
            self._on_volume_slider_value_change
        )
        self._mute_btn.clicked.connect(self._on_mute_checkbox_click)

    def _disconnect_ui_signals(self) -> None:
        self._volume_slider.valueChanged.disconnect(
            self._on_volume_slider_value_change
        )
        self._mute_btn.clicked.disconnect(self._on_mute_checkbox_click)

    def _on_volume_slider_value_change(self) -> None:
        self._api.playback.volume = self._volume_slider.value()

    def _on_mute_checkbox_click(self) -> None:
        self._api.playback.is_muted = self._mute_btn.isChecked()

    def _on_video_volume_change(self) -> None:
        self._disconnect_ui_signals()
        self._volume_slider.setValue(floor(float(self._api.playback.volume)))
        self._connect_ui_signals()

    def _on_video_mute_change(self) -> None:
        self._disconnect_ui_signals()
        self._mute_btn.setChecked(self._api.playback.is_muted)
        self._mute_btn.setIcon(
            get_icon("muted" if self._mute_btn.isChecked() else "unmuted")
        )
        self._connect_ui_signals()


class Video(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._api = api
        self._controller = VideoMouseModeController(api, self)

        self.setObjectName("video-container")

        self._video_preview = VideoPreview(api, self._controller, self)
        self._volume_control = VideoVolumeControl(api, self)
        self._mode_btns = VideoModeButtons(api, self._controller, self)
        self._playback_btns = VideoPlaybackButtons(api, self)

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self._mode_btns)
        left_layout.addWidget(self._volume_control)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self._video_preview)
        right_layout.addWidget(self._playback_btns)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
