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


class VideoInteractionMode(enum.IntEnum):
    Zoom = 1
    Pan = 2


class VideoController(QtCore.QObject):
    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._api = api

        self.mode: T.Optional[VideoInteractionMode] = None

    def on_wheel_turn(self, x: float, y: float) -> None:
        if self.mode == VideoInteractionMode.Zoom:
            self._api.video.view.zoom += y / 15 / 100
        elif self.mode == VideoInteractionMode.Pan:
            self._api.video.view.pan_x += x / 15 / 100
            self._api.video.view.pan_y += y / 15 / 100


class VideoPreview(MpvWidget):
    def __init__(
        self, api: Api, controller: VideoController, parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(api, parent)
        self._controller = controller

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400, 300)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        self._controller.on_wheel_turn(
            event.angleDelta().x(), event.angleDelta().y()
        )


class VideoModeButtons(QtWidgets.QToolBar):
    def __init__(
        self, api: Api, controller: VideoController, parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._controller = controller

        self.setOrientation(QtCore.Qt.Vertical)

        self._btn_group = QtWidgets.QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._btn_group.buttonToggled.connect(self._on_mode_btn_toggle)

        self._add_action_btn(
            "reset", "Reset video view", self._on_reset_btn_click
        )
        self._add_mode_btn("zoom-in", "Zoom video", VideoInteractionMode.Zoom)
        self._add_mode_btn("move", "Pan video", VideoInteractionMode.Pan)

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

        self._play_btn = QtWidgets.QPushButton("Play", self)
        self._play_btn.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        )
        self._play_btn.setCheckable(True)

        self._pause_btn = QtWidgets.QPushButton("Pause", self)
        self._pause_btn.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause)
        )
        self._pause_btn.setCheckable(True)

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
        layout.addWidget(self._play_btn)
        layout.addWidget(self._pause_btn)
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
        self._play_btn.clicked.connect(self._on_play_btn_click)
        self._pause_btn.clicked.connect(self._on_pause_btn_click)
        self._playback_speed_spinbox.valueChanged.connect(
            self._on_playback_speed_spinbox_change
        )
        self._sync_video_pos_checkbox.clicked.connect(
            self._on_sync_video_pos_checkbox_click
        )

    def _disconnect_ui_signals(self) -> None:
        self._play_btn.clicked.disconnect(self._on_play_btn_click)
        self._pause_btn.clicked.disconnect(self._on_pause_btn_click)
        self._playback_speed_spinbox.valueChanged.disconnect(
            self._on_playback_speed_spinbox_change
        )
        self._sync_video_pos_checkbox.clicked.disconnect(
            self._on_sync_video_pos_checkbox_click
        )

    def _on_play_btn_click(self) -> None:
        self._api.playback.is_paused = False
        self._on_video_pause_change()

    def _on_pause_btn_click(self) -> None:
        self._api.playback.is_paused = True
        self._on_video_pause_change()

    def _on_playback_speed_spinbox_change(self) -> None:
        self._api.playback.playback_speed = (
            self._playback_speed_spinbox.value()
        )
        self._on_video_playback_speed_change()

    def _on_video_pause_change(self) -> None:
        self._disconnect_ui_signals()
        self._play_btn.setChecked(not self._api.playback.is_paused)
        self._pause_btn.setChecked(self._api.playback.is_paused)
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
            self.style().standardIcon(
                QtWidgets.QStyle.SP_MediaVolumeMuted
                if self._mute_btn.isChecked()
                else QtWidgets.QStyle.SP_MediaVolume
            )
        )
        self._connect_ui_signals()


class Video(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._controller = VideoController(api, self)

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
