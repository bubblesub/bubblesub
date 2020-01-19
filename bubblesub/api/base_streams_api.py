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

# TODO: remove this condition when switching to Python 3.7
if T.TYPE_CHECKING:

    class TStream(T.Protocol):  # pylint: disable=no-member
        """Base stream protocol."""

        uid: uuid.UUID
        loaded: QtCore.pyqtSignal
        changed: QtCore.pyqtSignal
        errored: QtCore.pyqtSignal

    _TStream = T.TypeVar("_TStream", bound="TStream")

    BaseStreamsApiTypeHint: T.Any = T.Generic[_TStream]
else:
    # Python 3.6 compatibility
    BaseStreamsApiTypeHint = object
    TStream = object


class BaseStreamsApi(QtCore.QObject, BaseStreamsApiTypeHint):
    """Common functions for audio and video stream manager APIs."""

    stream_lock = threading.RLock()

    current_stream_switched = QtCore.pyqtSignal(object)

    stream_created = QtCore.pyqtSignal(object)
    stream_changed = QtCore.pyqtSignal(object)
    stream_loaded = QtCore.pyqtSignal(object)
    stream_unloaded = QtCore.pyqtSignal(object)

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__()
        self._streams: T.List[TStream] = []
        self._current_stream: T.Optional[TStream] = None

    @synchronized(lock=stream_lock)
    def unload_all_streams(self) -> None:
        """Unload all loaded streams."""
        for stream in self._streams:
            self.stream_unloaded.emit(stream)
        self._streams = []
        self.switch_stream(None)

    @synchronized(lock=stream_lock)
    def load_stream(self, path: Path, switch: bool = True) -> bool:
        """Load stream from specified file.

        :param path: path to load the stream from
        :param switch: whether to switch to that stream immediately
        :return: False if stream was already loaded, True otherwise
        """
        for stream in self._streams:
            if stream.path.samefile(path):
                if switch:
                    self.switch_stream(stream.uid)
                return False

        stream = self._create_stream(path)
        stream.loaded.connect(partial(self._on_stream_load, stream))
        stream.errored.connect(partial(self._on_stream_error, stream))
        stream.changed.connect(partial(self._on_stream_change, stream))
        self._streams.append(stream)
        self.stream_created.emit(stream)

        if switch:
            self.switch_stream(stream.uid)

        return True

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
        if index is None:
            return
        old_stream = self._streams[index]
        self._streams = [
            stream for stream in self._streams if stream.uid != uid
        ]
        if index < len(self._streams):
            self.switch_stream(self._streams[index].uid)
        else:
            self.switch_stream(None)
        self.stream_unloaded.emit(old_stream)

    @synchronized(lock=stream_lock)
    def switch_stream(self, uid: T.Optional[uuid.UUID]) -> None:
        """Switches streams.

        :param uid: stream to switch to
        """
        if uid is None:
            self._set_current_stream(None)
        else:
            stream: T.Optional[TStream]
            for stream in self._streams:
                if stream.uid == uid:
                    break
            else:
                stream = None
            if not stream:
                raise ValueError(f"stream {uid} is not loaded")
            self._set_current_stream(stream)

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

    def _set_current_stream(self, stream: T.Optional[TStream]) -> None:
        if stream != self._current_stream:
            self._current_stream = stream
            self.current_stream_switched.emit(self._current_stream)

    @synchronized(lock=stream_lock)
    def _on_stream_load(self, stream: TStream) -> None:
        self.stream_loaded.emit(stream)

    @synchronized(lock=stream_lock)
    def _on_stream_error(self, stream: TStream) -> None:
        self.unload_stream(stream.uid)

    @synchronized(lock=stream_lock)
    def _on_stream_change(self, stream: TStream) -> None:
        self.stream_changed.emit(stream)

    def _create_stream(self, path: Path) -> TStream:
        raise NotImplementedError

    @synchronized(lock=stream_lock)
    def cycle_streams(self) -> None:
        """Cycle to next available stream.

        Does nothing if there are no loaded streams.
        """
        if not self.current_stream:
            return
        uid = self.current_stream.uid
        idx = self.get_stream_index(uid)
        assert idx is not None
        idx += 1
        idx %= len(self.streams)
        uid = self.streams[idx].uid
        self.switch_stream(uid)
