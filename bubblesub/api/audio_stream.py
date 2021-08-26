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

"""Audio stream."""

import threading
import time
import uuid
from contextlib import nullcontext
from pathlib import Path
from typing import IO, ContextManager, Optional, Union, cast

import ffms2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from bubblesub.api.log import LogApi
from bubblesub.api.threading import ThreadingApi
from bubblesub.fmt.wav import write_wav

_LOADING = object()
_SAMPLER_LOCK = threading.Lock()


def _load_audio_source(
    log_api: LogApi, uid: uuid.UUID, path: Path
) -> Optional[ffms2.AudioSource]:
    """Create FFMS audio source.

    :param log_api: logging API
    :param uid: uid of the stream (for logging)
    :param path: path to the audio file
    :return: resulting FFMS audio source or None if failed to create
    """
    log_api.info(f"audio {uid} started loading ({path})")

    if not path.exists():
        log_api.error(f"error loading audio {uid} (file {path} not found)")
        return None

    try:
        indexer = ffms2.Indexer(str(path))
        for track in indexer.track_info_list:
            indexer.track_index_settings(track.num, 1, 0)
        index = indexer.do_indexing2()
    except ffms2.Error as ex:
        log_api.error(f"error loading audio {uid} ({ex})")
        return None

    try:
        track_number = index.get_first_indexed_track_of_type(
            ffms2.FFMS_TYPE_AUDIO
        )
        source = ffms2.AudioSource(str(path), track_number, index)
    except ffms2.Error as ex:
        log_api.error(f"error loading audio {uid} ({ex})")
        return None
    else:
        log_api.info(f"audio {uid} finished loading")
        return source


class AudioStream(QObject):
    """The audio source."""

    errored = pyqtSignal()
    changed = pyqtSignal()
    loaded = pyqtSignal()

    def __init__(
        self, threading_api: ThreadingApi, log_api: LogApi, path: Path
    ) -> None:
        """Initialize self.

        :param threading_api: threading API
        :param log_api: logging API
        :param path: path to the audio file to load
        """
        super().__init__()
        self._threading_api = threading_api
        self._log_api = log_api

        self.uid = uuid.uuid4()

        self._min_time = 0
        self._max_time = 0
        self._channel_count = 0
        self._bits_per_sample = 0
        self._sample_count = 0
        self._sample_rate = 0
        self._sample_format: Optional[int] = None
        self._path = path
        self._delay = 0

        self._source: Union[None, ffms2.AudioSource] = None

        self._log_api.info(f"audio: loading {path}")
        self._threading_api.schedule_task(
            lambda: _load_audio_source(self._log_api, self.uid, self._path),
            self._got_source,
        )

    @property
    def path(self) -> Path:
        """Return audio source path.

        :return: path
        """
        return self._path

    @property
    def is_ready(self) -> bool:
        """Return whether if the audio is loaded.

        :return: whether if the audio is loaded
        """
        return self._source is not None

    @property
    def channel_count(self) -> int:
        """Return channel count for currently loaded audio source.

        :return: channel count or 0 if no audio source
        """
        return self._channel_count

    @property
    def bits_per_sample(self) -> int:
        """Return bits per sample for currently loaded audio source.

        :return: bits per sample or 0 if no audio source
        """
        return self._bits_per_sample

    @property
    def sample_rate(self) -> int:
        """Return sample rate for currently loaded audio source.

        :return: sample rate or 0 if no audio source
        """
        return self._sample_rate

    @property
    def sample_format(self) -> Optional[int]:
        """Return sample format for currently loaded audio source.

        :return: sample format or None if no audio source
        """
        return self._sample_format

    @property
    def sample_count(self) -> int:
        """Return sample count for currently loaded audio source.

        :return: sample count or 0 if no audio source
        """
        return self._sample_count

    @property
    def min_time(self) -> int:
        """Return minimum time in milliseconds (generally 0).

        :return: audio start or 0 if no audio source
        """
        return self._min_time

    @property
    def max_time(self) -> int:
        """Return maximum time in milliseconds.

        :return: audio end or 0 if no audio source
        """
        return self._max_time

    @property
    def delay(self) -> int:
        """Return user-configured stream delay in milliseconds.

        :return: stream delay
        """
        return self._delay

    @delay.setter
    def delay(self, value: int) -> None:
        """Set new stream delay in milliseconds.

        :param value: new stream delay
        """
        self._delay = value
        self.changed.emit()

    def get_samples(self, start_frame: int, count: int) -> np.array:
        """Get raw audio samples from the currently loaded audio source.
        Doesn't take delay into account.

        :param start_frame: start frame (not PTS)
        :param count: how many samples to get
        :return: numpy array of samples
        """
        with _SAMPLER_LOCK:
            self._wait_for_source()
            if not self._source:
                channel_count = max(1, self.channel_count)
                return np.zeros(count * channel_count).reshape(
                    (count, channel_count)
                )
            if start_frame + count > self.sample_count:
                count = max(0, self.sample_count - start_frame)
            if not count:
                return self._create_empty_sample_buffer()
            self._source.init_buffer(count)
            return self._source.get_audio(start_frame)

    def save_wav(
        self,
        path_or_handle: Union[Path, IO[bytes]],
        start_pts: int,
        end_pts: int,
    ) -> None:
        """Save samples for the currently loaded audio source as WAV file.
        Takes user-configured delay into account.

        :param path_or_handle: where to put the result WAV file in
        :param start_pts: start PTS
        :param end_pts: end PTS
        """
        start_pts -= self.delay
        end_pts -= self.delay
        start_frame = int(start_pts * self.sample_rate / 1000)
        end_frame = int(end_pts * self.sample_rate / 1000)
        frame_count = end_frame - start_frame
        if frame_count < 0:
            raise ValueError("negative number of frames")
        samples = self.get_samples(start_frame, frame_count)

        # increase compatibility with external programs
        if samples.dtype.name in ("float32", "float64"):
            samples = (samples * (1 << 31)).astype(np.int32)

        ctx: ContextManager[IO[bytes]]
        if isinstance(path_or_handle, Path):
            ctx = path_or_handle.open("wb")
        else:
            ctx = nullcontext(path_or_handle)

        with ctx as handle:
            write_wav(handle, self.sample_rate, samples)

    def _create_empty_sample_buffer(self) -> np.array:
        return np.zeros(
            0,
            dtype={
                ffms2.FFMS_FMT_U8: np.uint8,
                ffms2.FFMS_FMT_S16: np.int16,
                ffms2.FFMS_FMT_S32: np.int32,
                ffms2.FFMS_FMT_FLT: np.float32,
                ffms2.FFMS_FMT_DBL: np.float64,
            }[self.sample_format],
        ).reshape(0, max(1, self.channel_count))

    def _got_source(self, source: Optional[ffms2.AudioSource]) -> None:
        self._source = source

        if source is None:
            self.errored.emit()
            return

        self._min_time = round(cast(float, source.properties.FirstTime) * 1000)
        self._max_time = round(cast(float, source.properties.LastTime) * 1000)
        self._channel_count = cast(int, source.properties.Channels)
        self._bits_per_sample = cast(int, source.properties.BitsPerSample)
        self._sample_count = cast(int, source.properties.NumSamples)
        self._sample_rate = cast(int, source.properties.SampleRate)
        self._sample_format = cast(
            Optional[int], source.properties.SampleFormat
        )
        self.loaded.emit()

    def _wait_for_source(self) -> bool:
        if self._source is None:
            return False
        while self._source is _LOADING:
            time.sleep(0.01)
        if self._source is None:
            return False
        return True
