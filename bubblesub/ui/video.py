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

import ctypes
import typing as T
from math import floor

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.audio import AudioState
from bubblesub.api.playback import (
    MAX_PLAYBACK_SPEED,
    MAX_VOLUME,
    MIN_PLAYBACK_SPEED,
    MIN_VOLUME,
    PlaybackFrontendState,
)
from bubblesub.api.video import VideoState
from bubblesub.ass_renderer import AssRenderer
from bubblesub.ui.mpv import MpvWidget


class _VideoPreviewMpv(MpvWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(api, parent)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400, 300)


class _VideoPreview(QtWidgets.QLabel):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self._api = api
        self._timer = QtCore.QTimer()
        self._timer.setTimerType(QtCore.Qt.PreciseTimer)
        self._timer.timeout.connect(self._on_next_frame)
        self._cur_frame_idx = 0
        self._end_frame_idx: T.Optional[int] = None
        self._ass_renderer = AssRenderer()

        api.subs.meta_changed.connect(self._on_subs_change)
        api.subs.events.item_changed.connect(self._on_subs_change)
        api.subs.events.items_inserted.connect(self._on_subs_change)
        api.subs.events.items_removed.connect(self._on_subs_change)
        api.subs.events.items_moved.connect(self._on_subs_change)
        api.subs.styles.item_changed.connect(self._on_subs_change)
        api.subs.styles.items_inserted.connect(self._on_subs_change)
        api.subs.styles.items_removed.connect(self._on_subs_change)
        api.subs.styles.items_moved.connect(self._on_subs_change)

        api.video.state_changed.connect(self._on_video_state_change)
        api.audio.state_changed.connect(self._on_audio_state_change)
        api.playback.request_seek.connect(self._on_request_seek)
        api.playback.request_playback.connect(self._on_request_playback)
        api.playback.playback_speed_changed.connect(
            self._on_playback_speed_change
        )
        api.playback.volume_changed.connect(self._on_volume_change)
        api.playback.mute_changed.connect(self._on_mute_change)
        api.playback.pause_changed.connect(self._on_pause_change)

    def _on_subs_change(self) -> None:
        # TODO: make this faster
        self._ass_renderer.set_source(
            self._api.subs.styles,
            self._api.subs.events,
            self._api.subs.meta,
            (self.width(), self.height()),
        )

    @property
    def cur_frame_idx(self) -> T.Optional[int]:
        return self._cur_frame_idx

    @cur_frame_idx.setter
    def cur_frame_idx(self, value: T.Optional[int]) -> None:
        self._cur_frame_idx = value
        self._api.playback.receive_current_pts_change.emit(
            self._api.video.timecodes[self._cur_frame_idx]
        )

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._on_subs_change()
        self._render_frame()

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400, 300)

    def _on_video_state_change(self, state: VideoState) -> None:
        self._sync_media()

    def _on_audio_state_change(self, state: AudioState) -> None:
        self._sync_media()

    def _sync_media(self) -> None:
        if (
            self._api.audio.state == AudioState.Loading
            or self._api.video.state == VideoState.Loading
        ):
            self._api.playback.state = PlaybackFrontendState.Loading
        else:
            self._api.playback.state = PlaybackFrontendState.Ready
        if self._api.video.state == VideoState.Loaded:
            self._timer.setInterval(float(self._api.video.frame_rate))
        else:
            self._timer.stop()

    def _on_request_seek(self, pts: int, precise: bool) -> None:
        self.cur_frame_idx = self._api.video.frame_idx_from_pts(pts)
        self._render_frame()

    def _on_request_playback(
        self, start_pts: T.Optional[int], end_pts: T.Optional[int]
    ) -> None:
        self._api.playback.is_paused = False
        if start_pts is not None:
            self.cur_frame_idx = self._api.video.frame_idx_from_pts(start_pts)
        if end_pts is not None:
            self._end_frame_idx = self._api.video.frame_idx_from_pts(end_pts)
        else:
            self._end_frame_idx = None
        self._timer.start()

    def _on_playback_speed_change(self) -> None:
        pass

    def _on_volume_change(self) -> None:
        pass

    def _on_mute_change(self) -> None:
        pass

    def _on_pause_change(self) -> None:
        self._end_frame_idx = None
        if self._api.playback.is_paused:
            self._timer.stop()
        else:
            self._timer.start()

    def _on_next_frame(self) -> None:
        self._render_frame()
        if (
            self._end_frame_idx is not None
            and self.cur_frame_idx + 1 >= self._end_frame_idx
        ):
            self._api.playback.is_paused = True
            self._timer.stop()
        else:
            self.cur_frame_idx += 1

    def _render_frame(self) -> None:
        frame = self._api.video.get_frame(
            self.cur_frame_idx, self.width(), self.height()
        )
        if frame is None:
            return
        frame = frame.copy()

        subs_overlay = self._ass_renderer.render_numpy(
            self._api.playback.current_pts
        )

        src_color = subs_overlay[..., :3].astype(np.float32) / 255.0
        src_alpha = subs_overlay[..., 3].astype(np.float32) / 255.0
        dst_color = frame[..., :3] / 255.0

        out_color = src_color * src_alpha[..., None] + dst_color * (
            1.0 - src_alpha[..., None]
        )

        frame[..., :3] = out_color * 255

        img = QtGui.QImage(
            frame.flatten(),
            frame.shape[1],
            frame.shape[0],
            frame.strides[0],
            QtGui.QImage.Format_RGB888,
        )
        pix = QtGui.QPixmap.fromImage(img)
        self.setPixmap(pix)

    def shutdown(self) -> None:
        pass


class _VideoButtons(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
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


class _VideoVolumeControl(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
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
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
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
