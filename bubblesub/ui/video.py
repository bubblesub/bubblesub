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


class VideoPreview(MpvWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(api.media.video.get_opengl_context(), parent)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400, 300)


class Video(QtWidgets.QWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)

        self._api = api

        self._video_preview = VideoPreview(api, self)
        self._volume_slider = QtWidgets.QSlider()
        self._volume_slider.setMinimum(0)
        self._volume_slider.setMaximum(200)
        self._volume_slider.setToolTip('Volume')

        self._mute_btn = QtWidgets.QPushButton(self)
        self._mute_btn.setCheckable(True)
        self._mute_btn.setToolTip('Mute')
        self._mute_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum
        )

        sublayout = QtWidgets.QVBoxLayout()
        sublayout.addWidget(self._volume_slider)
        sublayout.addWidget(self._mute_btn)
        sublayout.setAlignment(self._volume_slider, QtCore.Qt.AlignHCenter)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(sublayout)
        layout.addWidget(self._video_preview)

        self._connect_signals()
        self._on_video_volume_change()
        self._on_video_mute_change()

        # TODO: buttons for play/pause like aegisub

    def shutdown(self) -> None:
        self._video_preview.shutdown()

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
        self._mute_btn.setChecked(self._api.media.mute)
        self._mute_btn.setIcon(
            self.style().standardIcon(
                QtWidgets.QStyle.SP_MediaVolumeMuted
                if self._mute_btn.isChecked() else
                QtWidgets.QStyle.SP_MediaVolume
            )
        )

    def _on_mute_checkbox_click(self) -> None:
        self._api.media.mute = self._mute_btn.isChecked()
