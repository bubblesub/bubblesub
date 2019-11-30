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

"""Audio API."""

import threading
import typing as T
from functools import partial
from pathlib import Path

from PyQt5 import QtCore

from bubblesub.api.audio_stream import AudioStream
from bubblesub.api.log import LogApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.api.threading import ThreadingApi, synchronized

_STREAMS_LOCK = threading.RLock()


class AudioApi(QtCore.QObject):
    """The audio API."""

    state_changed = QtCore.pyqtSignal()

    def __init__(
        self,
        threading_api: ThreadingApi,
        log_api: LogApi,
        subs_api: SubtitlesApi,
    ) -> None:
        """Initialize self.

        :param threading_api: threading API
        :param log_api: logging API
        :param subs_api: subtitles API
        """
        super().__init__()
        self._threading_api = threading_api
        self._log_api = log_api
        self._subs_api = subs_api

        self._streams: T.List[AudioStream] = []
        self._current_stream_index: T.Optional[int] = None

    @synchronized(lock=_STREAMS_LOCK)
    def unload_all_streams(self) -> None:
        """Unload all loaded audio streams."""
        self._streams = []
        self._current_stream_index = None
        self.state_changed.emit()

    @synchronized(lock=_STREAMS_LOCK)
    def load_stream(
        self, path: T.Union[str, Path], switch: bool = True
    ) -> None:
        """Load audio stream from specified file.

        :param path: path to load the audio from
        :param switch: whether to switch to that stream immediately
        """
        # TODO: switch to stream when trying to load an already loaded source

        new_index = len(self._streams)
        stream = AudioStream(self._threading_api, self._log_api, path)
        stream.loaded.connect(partial(self._audio_stream_loaded, new_index))
        stream.errored.connect(partial(self._audio_stream_errored, new_index))
        stream.changed.connect(partial(self._audio_stream_changed, new_index))
        self._streams.append(stream)

        if switch:
            self._current_stream_index = new_index

        self.state_changed.emit()

    @synchronized(lock=_STREAMS_LOCK)
    def unload_stream(self, index: int) -> None:
        """Unload audio stream at the given index.

        :param index: stream to unload
        """
        if index < 0 or index >= len(self._streams):
            raise ValueError("stream index out of range")
        self._streams = self._streams[:index] + self._streams[index + 1 :]
        if self._current_stream_index >= index:
            self._current_stream_index -= 1
            if self._current_stream_index == -1:
                self._current_stream_index = None
        self.state_changed.emit()

    @synchronized(lock=_STREAMS_LOCK)
    def switch_stream(self, index: int) -> None:
        """Switches streams.

        :param index: stream to switch to
        """
        if index < 0 or index >= len(self._streams):
            raise ValueError("stream index out of range")
        self._current_stream_index = index
        self.state_changed.emit()

    @synchronized(lock=_STREAMS_LOCK)
    def unload_current_stream(self) -> None:
        """Unload currently loaded audio source."""
        if self._current_stream_index is not None:
            self.unload_stream(self._current_stream_index)

    @property
    @synchronized(lock=_STREAMS_LOCK)
    def current_stream_index(self) -> T.Optional[int]:
        """Return currently loaded stream index.

        :return: stream index
        """
        return self._current_stream_index

    @property
    @synchronized(lock=_STREAMS_LOCK)
    def current_stream(self) -> T.Optional[AudioStream]:
        """Return currently loaded stream.

        :return: stream
        """
        if self._current_stream_index is None:
            return None
        return self._streams[self._current_stream_index]

    @property
    @synchronized(lock=_STREAMS_LOCK)
    def streams(self) -> T.Iterable[AudioStream]:
        """Return all loaded streams.

        :return: list of streams
        """
        return self._streams[:]

    @synchronized(lock=_STREAMS_LOCK)
    def _audio_stream_loaded(self, index: int) -> None:
        self.state_changed.emit()
        self._subs_api.remember_audio_path_if_needed(self._streams[index].path)

    @synchronized(lock=_STREAMS_LOCK)
    def _audio_stream_errored(self, index: int) -> None:
        self.unload_stream(index)

    @synchronized(lock=_STREAMS_LOCK)
    def _audio_stream_changed(self, index: int) -> None:
        self.state_changed.emit()
