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

from math import floor

from PyQt5 import QtCore
from PyQt5 import QtWidgets

import bubblesub.api
from bubblesub.ui.mpv import MpvWidget


class _VideoPreview(MpvWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(api.media.video.get_opengl_context(), parent)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400, 300)


class _VideoButtons(QtWidgets.QWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)
        self._api = api

        self._play_btn = QtWidgets.QPushButton('Play', self)
        self._play_btn.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        )
        self._play_btn.setCheckable(True)

        self._pause_btn = QtWidgets.QPushButton('Pause', self)
        self._pause_btn.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause)
        )
        self._pause_btn.setCheckable(True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._play_btn)
        layout.addWidget(self._pause_btn)
        layout.addStretch()

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Maximum
        )

        self._play_btn.clicked.connect(self._on_play_btn_click)
        self._pause_btn.clicked.connect(self._on_pause_btn_click)
        self._api.media.pause_changed.connect(self._on_video_pause_change)
        self._on_video_pause_change()

    def _on_play_btn_click(self) -> None:
        self._api.media.is_paused = False
        self._on_video_pause_change()

    def _on_pause_btn_click(self) -> None:
        self._api.media.is_paused = True
        self._on_video_pause_change()

    def _on_video_pause_change(self) -> None:
        self._play_btn.setChecked(not self._api.media.is_paused)
        self._pause_btn.setChecked(self._api.media.is_paused)


class _VideoVolumeControl(QtWidgets.QWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)
        self._api = api

        self._volume_slider = QtWidgets.QSlider(self)
        self._volume_slider.setMinimum(0)
        self._volume_slider.setMaximum(200)
        self._volume_slider.setToolTip('Volume')

        self._mute_btn = QtWidgets.QPushButton(self)
        self._mute_btn.setCheckable(True)
        self._mute_btn.setToolTip('Mute')

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._volume_slider)
        layout.addWidget(self._mute_btn)
        layout.setAlignment(self._volume_slider, QtCore.Qt.AlignHCenter)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Minimum
        )

        self._connect_signals()
        self._on_video_volume_change()
        self._on_video_mute_change()

    def _connect_signals(self) -> None:
        self._volume_slider.valueChanged.connect(
            self._on_volume_slider_value_change
        )
        self._api.media.volume_changed.connect(self._on_video_volume_change)
        self._mute_btn.clicked.connect(self._on_mute_checkbox_click)
        self._api.media.mute_changed.connect(self._on_video_mute_change)

    def _disconnect_signals(self) -> None:
        self._volume_slider.valueChanged.disconnect(
            self._on_volume_slider_value_change
        )
        self._api.media.volume_changed.disconnect(self._on_video_volume_change)
        self._mute_btn.clicked.disconnect(self._on_mute_checkbox_click)
        self._api.media.mute_changed.disconnect(self._on_video_mute_change)

    def _on_video_volume_change(self) -> None:
        self._disconnect_signals()
        self._volume_slider.setValue(floor(float(self._api.media.volume)))
        self._connect_signals()

    def _on_volume_slider_value_change(self) -> None:
        self._api.media.volume = self._volume_slider.value()

    def _on_video_mute_change(self) -> None:
        self._disconnect_signals()
        self._mute_btn.setChecked(self._api.media.mute)
        self._mute_btn.setIcon(
            self.style().standardIcon(
                QtWidgets.QStyle.SP_MediaVolumeMuted
                if self._mute_btn.isChecked() else
                QtWidgets.QStyle.SP_MediaVolume
            )
        )
        self._connect_signals()

    def _on_mute_checkbox_click(self) -> None:
        self._api.media.mute = self._mute_btn.isChecked()


class Video(QtWidgets.QWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)
        self._api = api

        self._video_preview = _VideoPreview(api, self)
        self._volume_control = _VideoVolumeControl(api, self)
        self._buttons = _VideoButtons(api, self)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self._video_preview)
        right_layout.addWidget(self._buttons)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._volume_control)
        layout.addLayout(right_layout)

    def shutdown(self) -> None:
        self._video_preview.shutdown()
