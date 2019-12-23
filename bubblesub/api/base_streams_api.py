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

"""Common class for audio and video stream manager APIs."""

import threading
import typing as T
import uuid
from functools import partial
from pathlib import Path

from PyQt5 import QtCore

from bubblesub.api.threading import synchronized

if T.TYPE_CHECKING:

    class TStream(T.Protocol):
        """Base stream protocol."""

        uid: uuid.UUID
        loaded: QtCore.pyqtSignal
        changed: QtCore.pyqtSignal
        errored: QtCore.pyqtSignal

    _TStream = T.TypeVar("_TStream", bound="TStream")

    BaseStreamsApiTypeHint: T.Any = T.Generic[_TStream]
else:
    BaseStreamsApiTypeHint = object
    TStream = object


class BaseStreamsApi(QtCore.QObject, BaseStreamsApiTypeHint):
    """Common functions for audio and video stream manager APIs."""

    stream_lock = threading.RLock()
    state_changed = QtCore.pyqtSignal()

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__()
        self._streams: T.List[TStream] = []
        self._current_stream: T.Optional[TStream] = None

    @synchronized(lock=stream_lock)
    def unload_all_streams(self) -> None:
        """Unload all loaded streams."""
        self._streams = []
        self._current_stream = None
        self.state_changed.emit()

    @synchronized(lock=stream_lock)
    def load_stream(self, path: Path, switch: bool = True) -> None:
        """Load stream from specified file.

        :param path: path to load the stream from
        :param switch: whether to switch to that stream immediately
        """
        # TODO: switch to stream when trying to load an already loaded source

        stream = self._create_stream(path)
        stream.loaded.connect(partial(self._stream_loaded, stream))
        stream.errored.connect(partial(self._stream_errored, stream))
        stream.changed.connect(partial(self._stream_changed, stream))
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

    @synchronized(lock=stream_lock)
    def unload_stream(self, uid: uuid.UUID) -> None:
        """Unload stream with the given uid.

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

    @synchronized(lock=stream_lock)
    def switch_stream(self, uid: uuid.UUID) -> None:
        """Switches streams.

        :param uid: stream to switch to
        """
        stream: T.Optional[TStream]
        for stream in self._streams:
            if stream.uid == uid:
                break
        else:
            stream = None
        if not stream:
            raise ValueError(f"stream {uid} is not loaded")
        self._current_stream = stream
        self.state_changed.emit()

    @synchronized(lock=stream_lock)
    def unload_current_stream(self) -> None:
        """Unload currently loaded stream."""
        if self._current_stream is not None:
            self.unload_stream(self._current_stream.uid)

    @property
    @synchronized(lock=stream_lock)
    def current_stream(self) -> T.Optional[TStream]:
        """Return currently loaded stream.

        :return: stream
        """
        return self._current_stream

    @property
    @synchronized(lock=stream_lock)
    def streams(self) -> T.Iterable[TStream]:
        """Return all loaded streams.

        :return: list of streams
        """
        return self._streams[:]

    @synchronized(lock=stream_lock)
    def _stream_loaded(self, stream: TStream) -> None:
        self.state_changed.emit()

    @synchronized(lock=stream_lock)
    def _stream_errored(self, stream: TStream) -> None:
        self.unload_stream(stream)

    @synchronized(lock=stream_lock)
    def _stream_changed(self, stream: TStream) -> None:
        self.state_changed.emit()

    def _create_stream(self, path: Path) -> TStream:
        raise NotImplementedError
