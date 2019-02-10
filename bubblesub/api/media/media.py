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

"""Media API. Exposes audio/video player."""

import fractions
import typing as T
from pathlib import Path

from PyQt5 import QtCore

from bubblesub.api.log import LogApi
from bubblesub.api.media.audio import AudioApi
from bubblesub.api.media.state import MediaState
from bubblesub.api.media.video import VideoApi
from bubblesub.api.subs import SubtitlesApi

MIN_PLAYBACK_SPEED = fractions.Fraction(0.1)
MAX_PLAYBACK_SPEED = fractions.Fraction(10)
MIN_VOLUME = fractions.Fraction(0)
MAX_VOLUME = fractions.Fraction(200)


class MediaApi(QtCore.QObject):
    """The media API."""

    state_changed = QtCore.pyqtSignal(MediaState)
    current_pts_changed = QtCore.pyqtSignal()
    max_pts_changed = QtCore.pyqtSignal()
    volume_changed = QtCore.pyqtSignal()
    pause_changed = QtCore.pyqtSignal()
    mute_changed = QtCore.pyqtSignal()
    playback_speed_changed = QtCore.pyqtSignal()

    # hooks for ui renderer
    request_seek = QtCore.pyqtSignal(int, bool)
    request_playback = QtCore.pyqtSignal(object, object)
    receive_current_pts_change = QtCore.pyqtSignal(int)
    receive_max_pts_change = QtCore.pyqtSignal(int)
    receive_ready = QtCore.pyqtSignal()

    def __init__(self, subs_api: SubtitlesApi, log_api: LogApi) -> None:
        """
        Initialize self.

        :param subs_api: subtitles API
        :param log_api: logging API
        """
        super().__init__()
        self._state = MediaState.Unloaded

        self._log_api = log_api
        self._subs_api = subs_api

        self._path: T.Optional[Path] = None
        self._playback_speed = fractions.Fraction(1.0)
        self._volume = fractions.Fraction(100.0)
        self._is_muted = False
        self._is_paused = True
        self._current_pts = 0
        self._max_pts = 0

        self._subs_api.loaded.connect(self._on_subs_load)
        self.receive_current_pts_change.connect(self._on_current_pts_change)
        self.receive_max_pts_change.connect(self._on_max_pts_change)
        self.receive_ready.connect(self._on_ready)

        self.video = VideoApi(self, log_api)
        self.audio = AudioApi(self, log_api, subs_api)

    def shutdown(self) -> None:
        """Stop internal worker threads."""
        self.audio.shutdown()
        self.video.shutdown()

    def unload(self) -> None:
        """Unload currently loaded video."""
        self.state = MediaState.Unloaded
        self.state_changed.emit(self.state)
        self._current_pts = 0
        self._max_pts = 0
        self._path = None

    def load(self, path: T.Union[str, Path]) -> None:
        """
        Load video.

        :param path: path where to load the video from
        """
        assert path is not None

        self.unload()

        self.state = MediaState.Loading
        self._path = Path(path)
        if str(self._subs_api.remembered_video_path) != str(self._path):
            self._subs_api.remembered_video_path = self._path

        self.state_changed.emit(self.state)

    def seek(self, pts: int, precise: bool = True) -> None:
        """
        Seek to specified position in the video.

        :param pts: PTS to seek to
        :param precise: whether to be preciser at the expense of performance
        """
        pts = max(0, pts)
        pts = self.video.align_pts_to_near_frame(pts)
        if pts != self.current_pts:
            self.request_seek.emit(pts, precise)

    def play(self, start: int, end: T.Optional[int]) -> None:
        """
        Play the currently loaded video at specified PTS range.

        :param start: start PTS
        :param end: end PTS
        """
        self.request_playback.emit(start, end)

    @property
    def state(self) -> MediaState:
        """
        Return current media state.

        :return: media state
        """
        return self._state

    @state.setter
    def state(self, value: MediaState) -> None:
        """
        Set current media state.

        :param value: new media state
        """
        self._log_api.debug(f"video: changed state to {value}")
        self._state = value

    @property
    def playback_speed(self) -> fractions.Fraction:
        """
        Return playback rate for the currently loaded video.

        :return: playback rate for the currently loaded video, 1.0 if no video
        """
        return self._playback_speed

    @playback_speed.setter
    def playback_speed(
        self, value: T.Union[fractions.Fraction, int, float]
    ) -> None:
        """
        Set new playback rate for the currently loaded video.

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
        """
        Return volume for the currently loaded video.

        :return: volume for the currently loaded video, 100.0 if no video
        """
        return self._volume

    @volume.setter
    def volume(self, value: T.Union[fractions.Fraction, int, float]) -> None:
        """
        Set new volume for the currently loaded video.

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
        """
        Return whether the video is muted.

        :return: whether the video is muted
        """
        return self._is_muted

    @is_muted.setter
    def is_muted(self, value: bool) -> None:
        """
        Mute or unmute the video.

        :param value: whether to mute the video
        """
        if value != self._is_muted:
            self._is_muted = value
            self.mute_changed.emit()

    @property
    def current_pts(self) -> int:
        """
        Return current video position.

        :return: current video position, 0 if no video
        """
        return self._current_pts

    @property
    def max_pts(self) -> int:
        """
        Return maximum video position.

        :return: maximum video position, 0 if no video
        """
        return self._max_pts

    @property
    def is_paused(self) -> bool:
        """
        Return whether the currently loaded video is paused.

        :return: whether the currently loaded video is paused, True if no video
        """
        return self._is_paused

    @is_paused.setter
    def is_paused(self, value: bool) -> None:
        """
        Pause or unpause the video.

        :param value: whether to pause the video
        """
        if value != self._is_paused:
            self._is_paused = value
            self.pause_changed.emit()

    @property
    def path(self) -> T.Optional[Path]:
        """
        Return path to the currently loaded video.

        :return: path to the currently loaded video, None if no video
        """
        return self._path

    @property
    def is_loaded(self) -> bool:
        """
        Return whether there's video loaded.

        :return: whether there's video loaded
        """
        return self.state == MediaState.Loaded

    def _on_subs_load(self) -> None:
        if self._subs_api.remembered_video_path:
            self.load(self._subs_api.remembered_video_path)
        else:
            self.unload()

    def _on_current_pts_change(self, new_pts: int) -> None:
        if new_pts != self._current_pts:
            self._current_pts = new_pts
            self.current_pts_changed.emit()

    def _on_max_pts_change(self, new_pts: int) -> None:
        if new_pts != self._max_pts:
            self._max_pts = new_pts
            self.max_pts_changed.emit()

    def _on_ready(self) -> None:
        self.state = MediaState.Loaded
        self.state_changed.emit(self.state)
