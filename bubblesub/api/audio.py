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

import enum
import threading
import time
import typing as T
from pathlib import Path

import ffms
import numpy as np
from PyQt5 import QtCore

from bubblesub.api.log import LogApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.cache import get_cache_file_path
from bubblesub.util import sanitize_file_name
from bubblesub.worker import Worker

_LOADING = object()
_SAMPLER_LOCK = threading.Lock()


class AudioState(enum.Enum):
    NotLoaded = enum.auto()
    Loading = enum.auto()
    Loaded = enum.auto()


class AudioSourceWorker(Worker):
    """Detached audio source provider."""

    def __init__(self, log_api: "LogApi") -> None:
        """
        Initialize self.

        :param log_api: logging API
        """
        super().__init__()
        self._log_api = log_api

    def _do_work(
        self, task: T.Any
    ) -> T.Tuple[Path, T.Optional[ffms.AudioSource]]:
        """
        Create audio source.

        :param task: path to the audio file
        :return: audio source
        """
        path = T.cast(Path, task)
        self._log_api.info(f"started loading audio ({path})")

        cache_path = get_cache_file_path(
            f"{sanitize_file_name(path)}-audio-index"
        )

        index = None
        if cache_path.exists():
            try:
                index = ffms.Index.read(
                    index_file=str(cache_path), source_file=str(path)
                )
                if not index.belongs_to_file(str(path)):
                    index = None
            except ffms.Error:
                index = None

        if not index:
            if not path.exists():
                self._log_api.error(f"audio file {path} not found")
                return (path, None)

            try:
                indexer = ffms.Indexer(str(path))
                index = indexer.do_indexing(-1)
            except ffms.Error as ex:
                self._log_api.error(f"audio couldn't be loaded: {ex}")
                return (path, None)
            else:
                cache_path.parent.mkdir(exist_ok=True, parents=True)
                index.write(str(cache_path))

        try:
            track_number = index.get_first_indexed_track_of_type(
                ffms.FFMS_TYPE_AUDIO
            )
            source = ffms.AudioSource(str(path), track_number, index)
        except ffms.Error as ex:
            self._log_api.error(f"audio couldn't be loaded: {ex}")
            return (path, None)
        else:
            self._log_api.info("audio finished loading")
            return (path, source)


class AudioApi(QtCore.QObject):
    """The audio API."""

    state_changed = QtCore.pyqtSignal(AudioState)

    def __init__(self, log_api: LogApi, subs_api: SubtitlesApi) -> None:
        """
        Initialize self.

        :param log_api: logging API
        :param subs_api: subtitles API
        """
        super().__init__()
        self._log_api = log_api
        self._subs_api = subs_api

        self._state = AudioState.NotLoaded
        self._path: T.Optional[Path] = None

        self._source: T.Union[None, ffms.AudioSource] = None
        self._source_worker = AudioSourceWorker(log_api)
        self._source_worker.task_finished.connect(self._got_source)
        self._source_worker.start()

    def unload(self) -> None:
        self._source = None
        self._path = None
        self.state = AudioState.NotLoaded

    def load(self, path: T.Union[str, Path]) -> None:
        """
        Load audio from specified file.

        :param path: path to load the audio from
        """
        self.unload()
        self._path = Path(path)

        self._log_api.info(f"audio: loading {path}")
        self.state = AudioState.Loading
        if (
            self._subs_api.remembered_audio_path is None
            or not self._path.samefile(self._subs_api.remembered_audio_path)
        ):
            self._subs_api.remembered_audio_path = self._path
        self._source_worker.schedule_task(self._path)

    def shutdown(self) -> None:
        """Stop internal worker threads."""
        self._source_worker.stop()

    @property
    def path(self) -> T.Optional[Path]:
        return self._path

    @property
    def state(self) -> AudioState:
        """
        Return current audio state.

        :return: audio state
        """
        return self._state

    @state.setter
    def state(self, value: AudioState) -> None:
        """
        Set current audio state.

        :param value: new audio state
        """
        if value != self._state:
            self._log_api.debug(f"audio: changed state to {value}")
            self._state = value
            self.state_changed.emit(self._state)

    @property
    def is_ready(self) -> bool:
        """
        Return whether if the audio is loaded.

        :return: whether if the audio is loaded
        """
        return self._state == AudioState.Loaded

    @property
    def channel_count(self) -> int:
        """
        Return channel count for currently loaded audio source.

        :return: channel count or 0 if no audio source
        """
        if not self._wait_for_source():
            return 0
        assert self._source
        return T.cast(int, self._source.properties.Channels)

    @property
    def bits_per_sample(self) -> int:
        """
        Return bits per sample for currently loaded audio source.

        :return: bits per sample or 0 if no audio source
        """
        if not self._wait_for_source():
            return 0
        assert self._source
        return T.cast(int, self._source.properties.BitsPerSample)

    @property
    def sample_rate(self) -> int:
        """
        Return sample rate for currently loaded audio source.

        :return: sample rate or 0 if no audio source
        """
        if not self._wait_for_source():
            return 0
        # other properties:
        # - ChannelLayout
        # - SampleFormat
        assert self._source
        return T.cast(int, self._source.properties.SampleRate)

    @property
    def sample_format(self) -> T.Optional[int]:
        """
        Return sample format for currently loaded audio source.

        :return: sample format or None if no audio source
        """
        if not self._wait_for_source():
            return None
        assert self._source
        return T.cast(T.Optional[int], self._source.properties.SampleFormat)

    @property
    def sample_count(self) -> int:
        """
        Return sample count for currently loaded audio source.

        :return: sample count or 0 if no audio source
        """
        if not self._wait_for_source():
            return 0
        assert self._source
        return T.cast(int, self._source.properties.NumSamples)

    @property
    def min_time(self) -> int:
        """
        Return minimum time in milliseconds.

        :return: audio start
        """
        if not self._wait_for_source():
            return 0
        return round(T.cast(float, self._source.properties.FirstTime) * 1000)

    @property
    def max_time(self) -> int:
        """
        Return maximum time in milliseconds.

        :return: audio end
        """
        if not self._wait_for_source():
            return 0
        return round(T.cast(float, self._source.properties.LastTime) * 1000)

    def get_samples(self, start_frame: int, count: int) -> np.array:
        """
        Get raw audio samples from the currently loaded audio source.

        :param start_frame: start frame (not PTS)
        :param count: how many samples to get
        :return: numpy array of samples
        """
        with _SAMPLER_LOCK:
            self._wait_for_source()
            if not self._source:
                return np.zeros(count).reshape(
                    (count, max(1, self.channel_count))
                )
            if start_frame + count > self.sample_count:
                count = max(0, self.sample_count - start_frame)
            if not count:
                return self._create_empty_sample_buffer()
            self._source.init_buffer(count)
            return self._source.get_audio(start_frame)

    def save_wav(
        self,
        path_or_handle: T.Union[Path, T.IO[str]],
        pts_ranges: T.List[T.Tuple[int, int]],
    ) -> None:
        """
        Save samples for the currently loaded audio source as WAV file.

        :param path_or_handle: where to put the WAV file in
        :param pts_ranges: list of start PTS / end PTS pairs to sample
        """
        samples = self._create_empty_sample_buffer()

        for pts_range in pts_ranges:
            start_pts, end_pts = pts_range
            start_frame = int(start_pts * self.sample_rate / 1000)
            end_frame = int(end_pts * self.sample_rate / 1000)
            frame_count = end_frame - start_frame
            samples = np.concatenate(
                (samples, self.get_samples(start_frame, frame_count))
            )

        # increase compatibility with external programs
        if samples.dtype.name in ("float32", "float64"):
            samples = (samples * (1 << 31)).astype(np.int32)

        # pylint: disable=no-member
        import scipy.io.wavfile

        scipy.io.wavfile.write(path_or_handle, self.sample_rate, samples)

    def _create_empty_sample_buffer(self) -> np.array:
        return np.zeros(
            0,
            dtype={
                ffms.FFMS_FMT_U8: np.uint8,
                ffms.FFMS_FMT_S16: np.int16,
                ffms.FFMS_FMT_S32: np.int32,
                ffms.FFMS_FMT_FLT: np.float32,
                ffms.FFMS_FMT_DBL: np.float64,
            }[self.sample_format],
        ).reshape(0, max(1, self.channel_count))

    def _got_source(
        self, result: T.Optional[T.Tuple[Path, ffms.AudioSource]]
    ) -> None:
        path, source = result
        if path != self._path:
            return

        self._source = source

        if source is None:
            self.state = AudioState.NotLoaded
        else:
            self.state = AudioState.Loaded

    def _wait_for_source(self) -> bool:
        if self._source is None:
            return False
        while self._source is _LOADING:
            time.sleep(0.01)
        if self._source is None:
            return False
        return True
