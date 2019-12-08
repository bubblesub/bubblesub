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

import uuid
import threading
import typing as T
from functools import partial
from pathlib import Path

from PyQt5 import QtCore

from bubblesub.api.audio_stream import AudioStream
from bubblesub.api.log import LogApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.api.threading import ThreadingApi, synchronized

STREAMS_LOCK = threading.RLock()


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
        self._current_stream: T.Optional[AudioStream] = None

    @synchronized(lock=STREAMS_LOCK)
    def unload_all_streams(self) -> None:
        """Unload all loaded audio streams."""
        self._streams = []
        self._current_stream = None
        self.state_changed.emit()

    @synchronized(lock=STREAMS_LOCK)
    def load_stream(
        self, path: T.Union[str, Path], switch: bool = True
    ) -> None:
        """Load audio stream from specified file.

        :param path: path to load the audio from
        :param switch: whether to switch to that stream immediately
        """
        # TODO: switch to stream when trying to load an already loaded source

        stream = AudioStream(self._threading_api, self._log_api, path)
        stream.loaded.connect(partial(self._audio_stream_loaded, stream))
        stream.errored.connect(partial(self._audio_stream_errored, stream))
        stream.changed.connect(partial(self._audio_stream_changed, stream))
        self._streams.append(stream)

        if switch:
            self._current_stream = stream

        self.state_changed.emit()

    def get_stream_index(self, uid: uuid.UUID) -> T.Optional[int]:
        """Returns index of the given stream uid.

        :param uid: stream to get the index of
        :return: stream index
        """
        uids = [stream.uid for stream in self._streams]
        try:
            return uids.index(uid)
        except ValueError:
            return None

    @synchronized(lock=STREAMS_LOCK)
    def unload_stream(self, uid: uuid.UUID) -> None:
        """Unload audio stream with the given uid.

        :param uid: stream to unload
        """
        index = self.get_stream_index(uid)
        self._streams = [
            stream for stream in self._streams if stream.uid != uuid
        ]
        if index is not None and index < len(self._streams):
            self._current_stream = self._streams[index]
        else:
            self._current_stream = None
        self.state_changed.emit()

    @synchronized(lock=STREAMS_LOCK)
    def switch_stream(self, uid: uuid.UUID) -> None:
        """Switches streams.

        :param uid: stream to switch to
        """
        for stream in self._streams:
            if stream.uid == uid:
                break
        else:
            stream = None
        if not stream:
            raise ValueError(f"stream {uid} is not loaded")
        self._current_stream = stream
        self.state_changed.emit()

    @synchronized(lock=STREAMS_LOCK)
    def unload_current_stream(self) -> None:
        """Unload currently loaded audio source."""
        if self._current_stream is not None:
            self.unload_stream(self._current_stream.uid)

    @property
    @synchronized(lock=STREAMS_LOCK)
    def current_stream(self) -> T.Optional[AudioStream]:
        """Return currently loaded stream.

        :return: stream
        """
        return self._current_stream

    @property
    @synchronized(lock=STREAMS_LOCK)
    def streams(self) -> T.Iterable[AudioStream]:
        """Return all loaded streams.

        :return: list of streams
        """
        return self._streams[:]

    @synchronized(lock=STREAMS_LOCK)
    def _audio_stream_loaded(self, stream: AudioStream) -> None:
        self.state_changed.emit()
        self._subs_api.remember_audio_path_if_needed(stream.path)

    @synchronized(lock=STREAMS_LOCK)
    def _audio_stream_errored(self, stream: AudioStream) -> None:
        self.unload_stream(stream)

    @synchronized(lock=STREAMS_LOCK)
    def _audio_stream_changed(self, stream: AudioStream) -> None:
        self.state_changed.emit()
