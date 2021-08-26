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

"""API for GUI spectrogram."""

from typing import Union

from PyQt5 import QtCore

from bubblesub.api.audio import AudioApi
from bubblesub.api.audio_stream import AudioStream
from bubblesub.api.subs import SubtitlesApi
from bubblesub.api.video import VideoApi
from bubblesub.api.video_stream import VideoStream


class AudioViewApi(QtCore.QObject):
    """API for spectrogram preview."""

    view_changed = QtCore.pyqtSignal()
    selection_changed = QtCore.pyqtSignal()

    def __init__(
        self, subs_api: SubtitlesApi, audio_api: AudioApi, video_api: VideoApi
    ) -> None:
        """Initialize self.

        :param subs_api: subtitles API
        :param audio_api: audio API
        :param video_api: video API
        """
        super().__init__()
        self._subs_api = subs_api
        self._audio_api = audio_api
        self._video_api = video_api

        self._min = 0
        self._max = 0
        self._view_start = 0
        self._view_end = 0
        self._selection_start = 0
        self._selection_end = 0

        audio_api.stream_loaded.connect(self._on_audio_state_change)
        video_api.stream_loaded.connect(self._on_video_state_change)
        subs_api.loaded.connect(self._on_subs_load)

        self.reset_view()

    @property
    def min(self) -> int:
        """Return minimum PTS.

        :return: minimum PTS
        """
        return self._min

    @property
    def max(self) -> int:
        """Return maximum PTS.

        :return: maximum PTS
        """
        return self._max

    @property
    def size(self) -> int:
        """Return how many PTS frames audio has.

        :return: how many PTS frames audio has
        """
        return self._max - self._min

    @property
    def view_start(self) -> int:
        """Return shown start PTS.

        :return: shown start PTS
        """
        return self._view_start

    @property
    def view_end(self) -> int:
        """Return shown end PTS.

        :return: shown end PTS
        """
        return self._view_end

    @property
    def view_size(self) -> int:
        """Return shown window size.

        :return: shown window size
        """
        return self._view_end - self._view_start

    @property
    def selection_start(self) -> int:
        """Return selection start PTS.

        :return: selection start PTS
        """
        return self._selection_start

    @property
    def selection_end(self) -> int:
        """Return selection end PTS.

        :return: selection end PTS
        """
        return self._selection_end

    @property
    def selection_size(self) -> int:
        """Return selection size.

        :return: selection size
        """
        return self._selection_end - self._selection_start

    def unselect(self) -> None:
        """Clear selection."""
        self._selection_start = 0
        self._selection_end = 0
        self.selection_changed.emit()

    def select(self, start_pts: int, end_pts: int) -> None:
        """Set new selection.

        :param start_pts: start PTS
        :param end_pts: end PTS
        """
        if start_pts > end_pts:
            end_pts, start_pts = start_pts, end_pts
        self._selection_start = self._clip(start_pts)
        self._selection_end = self._clip(end_pts)
        self.selection_changed.emit()

    def view(self, start_pts: int, end_pts: int) -> None:
        """Set new view window.

        :param start_pts: start PTS
        :param end_pts: end PTS
        """
        if start_pts > end_pts:
            end_pts, start_pts = start_pts, end_pts
        self._view_start = self._clip(start_pts)
        self._view_end = self._clip(end_pts)
        self.view_changed.emit()

    def zoom_view(self, factor: float, origin: float) -> None:
        """Zoom the view window.

        :param factor: zoom factor (>1 = zoom in, <1 = zoom out)
        :param origin: 0…1 relative to the view window
        """
        factor = max(0.001, min(1, factor))
        old_origin = self.view_start - self._min
        old_view_size = self.view_size * origin
        self._view_start = self.min
        self._view_end = self._clip(self.min + self.size * factor)
        new_view_size = self.view_size * origin
        distance = int(old_origin - new_view_size + old_view_size)
        self.move_view(distance)  # emits view_changed

    def move_view(self, distance: int) -> None:
        """Move the view window.

        :param distance: distance in PTS
        """
        view_size = self.view_size
        if self._view_start + distance < self.min:
            self.view(self.min, self.min + view_size)
        elif self._view_end + distance > self.max:
            self.view(self.max - view_size, self.max)
        else:
            self.view(self._view_start + distance, self._view_end + distance)

    def reset_view(self) -> None:
        """Resets the view to show the entire spectrogram."""
        self._min = 0
        self._max = 0
        self._extend_view()
        self.zoom_view(1, 0.5)  # emits view_changed

    def _extend_view(self) -> None:
        self._min = 0
        self._max = max(
            [self._max]
            + [
                self._video_api.current_stream.max_pts
                if self._video_api.current_stream
                else 0
            ]
            + [
                self._audio_api.current_stream.max_time
                if self._audio_api.current_stream
                else 0
            ]
            + [sub.start for sub in self._subs_api.events]
            + [sub.end for sub in self._subs_api.events]
        )

    def _on_audio_state_change(self, stream: AudioStream) -> None:
        if stream == self._audio_api.current_stream:
            self._extend_view()
            self.reset_view()

    def _on_video_state_change(self, stream: VideoStream) -> None:
        if stream == self._video_api.current_stream:
            self._extend_view()
            self.reset_view()

    def _on_subs_load(self) -> None:
        self.reset_view()
        self._subs_api.events.changed.subscribe(
            lambda _event: self._extend_view()
        )

    def _clip(self, value: Union[int, float]) -> int:
        return max(min(self._max, int(value)), self._min)
