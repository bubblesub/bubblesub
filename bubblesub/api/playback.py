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

"""Playback API. Exposes functions to interact with audio/video player."""

import enum
import fractions
from typing import Optional, Union

from PyQt5 import QtCore

from bubblesub.api.audio import AudioApi
from bubblesub.api.log import LogApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.api.video import VideoApi

MIN_PLAYBACK_SPEED = fractions.Fraction(0.1)
MAX_PLAYBACK_SPEED = fractions.Fraction(10)
MIN_VOLUME = fractions.Fraction(0)
MAX_VOLUME = fractions.Fraction(200)


class PlaybackFrontendState(enum.Enum):
    """State of media player."""

    NOT_READY = enum.auto()
    LOADING = enum.auto()
    READY = enum.auto()


class PlaybackApi(QtCore.QObject):
    """The playback API."""

    state_changed = QtCore.pyqtSignal(PlaybackFrontendState)
    current_pts_changed = QtCore.pyqtSignal()
    volume_changed = QtCore.pyqtSignal()
    pause_changed = QtCore.pyqtSignal(bool)
    mute_changed = QtCore.pyqtSignal()
    playback_speed_changed = QtCore.pyqtSignal()

    # hooks for ui renderer
    request_seek = QtCore.pyqtSignal(int, bool)
    request_playback = QtCore.pyqtSignal(object, object)
    receive_current_pts_change = QtCore.pyqtSignal(int)

    def __init__(
        self,
        log_api: LogApi,
        subs_api: SubtitlesApi,
        video_api: VideoApi,
        audio_api: AudioApi,
    ) -> None:
        """Initialize self.

        :param log_api: logging API
        :param subs_api: subtitles API
        :param video_api: video API
        :param audio_api: audio API
        """
        super().__init__()
        self._log_api = log_api
        self._subs_api = subs_api
        self._video_api = video_api
        self._audio_api = audio_api

        self._state = PlaybackFrontendState.NOT_READY
        self._playback_speed = fractions.Fraction(1.0)
        self._volume = fractions.Fraction(100.0)
        self._is_muted = False
        self._is_paused = True
        self._current_pts = 0

        self.receive_current_pts_change.connect(
            self._on_current_pts_change, QtCore.Qt.DirectConnection
        )

    def seek(self, pts: int, precise: bool = True) -> None:
        """Seek to specified position in the video.

        :param pts: PTS to seek to
        :param precise: whether to be preciser at the expense of performance
        """
        pts = max(0, pts)
        if pts != self.current_pts:
            self.request_seek.emit(pts, precise)

    def play(self, start: int, end: Optional[int]) -> None:
        """Play the currently loaded video at specified PTS range.

        :param start: start PTS
        :param end: end PTS
        """
        self.request_playback.emit(start, end)

    @property
    def state(self) -> PlaybackFrontendState:
        """Return current playback state.

        :return: playback state
        """
        return self._state

    @state.setter
    def state(self, value: PlaybackFrontendState) -> None:
        """Set current playback state.

        :param value: new playback state
        """
        if value != self._state:
            self._state = value
            self._log_api.debug(f"playback: changed state to {value}")
            self.state_changed.emit(self.state)

    @property
    def playback_speed(self) -> fractions.Fraction:
        """Return playback rate for the currently loaded video.

        :return: playback rate for the currently loaded video, 1.0 if no video
        """
        return self._playback_speed

    @playback_speed.setter
    def playback_speed(
        self, value: Union[fractions.Fraction, int, float]
    ) -> None:
        """Set new playback rate for the currently loaded video.

        :param value: new playback rate
        """
        if not isinstance(value, fractions.Fraction):
            value = fractions.Fraction(value)
        if value < MIN_PLAYBACK_SPEED:
            value = MIN_PLAYBACK_SPEED
        if value > MAX_PLAYBACK_SPEED:
            value = MAX_PLAYBACK_SPEED
        if value != self._playback_speed:
            self._playback_speed = value
            self.playback_speed_changed.emit()

    @property
    def volume(self) -> fractions.Fraction:
        """Return volume for the currently loaded video.

        :return: volume for the currently loaded video, 100.0 if no video
        """
        return self._volume

    @volume.setter
    def volume(self, value: Union[fractions.Fraction, int, float]) -> None:
        """Set new volume for the currently loaded video.

        :param value: new volume
        """
        if not isinstance(value, fractions.Fraction):
            value = fractions.Fraction(value)
        if value < MIN_VOLUME:
            value = MIN_VOLUME
        if value > MAX_VOLUME:
            value = MAX_VOLUME
        if value != self._volume:
            self._volume = value
            self.volume_changed.emit()

    @property
    def is_muted(self) -> bool:
        """Return whether the video is muted.

        :return: whether the video is muted
        """
        return self._is_muted

    @is_muted.setter
    def is_muted(self, value: bool) -> None:
        """Mute or unmute the video.

        :param value: whether to mute the video
        """
        if value != self._is_muted:
            self._is_muted = value
            self.mute_changed.emit()

    @property
    def current_pts(self) -> int:
        """Return current video position.

        :return: current video position, 0 if no video
        """
        return self._current_pts

    @property
    def max_pts(self) -> int:
        """Return maximum video position.

        :return: maximum video position, 0 if no video
        """
        return max(
            self._audio_api.current_stream.max_time
            if self._audio_api.current_stream
            else 0,
            self._video_api.current_stream.max_pts
            if self._video_api.current_stream
            else 0,
        )

    @property
    def is_paused(self) -> bool:
        """Return whether the currently loaded video is paused.

        :return: whether the currently loaded video is paused, True if no video
        """
        return self._is_paused

    @is_paused.setter
    def is_paused(self, value: bool) -> None:
        """Pause or unpause the video.

        :param value: whether to pause the video
        """
        if value != self._is_paused:
            self._is_paused = value
            self.pause_changed.emit(value)

    @property
    def is_ready(self) -> bool:
        """Return whether the playback frontend is ready.

        :return: whether the playback frontend is ready
        """
        return self._state == PlaybackFrontendState.READY

    def _on_current_pts_change(self, new_pts: int) -> None:
        if new_pts != self._current_pts:
            self._current_pts = new_pts
            self.current_pts_changed.emit()
