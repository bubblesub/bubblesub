import time
import threading
import typing as T
from pathlib import Path

import ffms
import scipy.io.wavfile
import numpy as np
from PyQt5 import QtCore

import bubblesub.api.log
import bubblesub.api.media.media
import bubblesub.cache
import bubblesub.util
import bubblesub.worker


_LOADING = object()
_SAMPLER_LOCK = threading.Lock()


class AudioSourceWorker(bubblesub.worker.Worker):
    def __init__(
            self,
            parent: QtCore.QObject,
            log_api: 'bubblesub.api.log.LogApi'
    ) -> None:
        super().__init__(parent)
        self._log_api = log_api

    def _do_work(self, task: T.Any) -> T.Any:
        path = T.cast(Path, task)
        self._log_api.info('audio/sampler: loading... ({})'.format(path))

        path_hash = bubblesub.util.hash_digest(path)
        cache_name = f'index-{path_hash}-audio'
        cache_path = bubblesub.cache.get_cache_file_path(cache_name)

        index = None
        if cache_path.exists():
            try:
                index = ffms.Index.read(
                    index_file=str(cache_path),
                    source_file=str(path)
                )
                if not index.belongs_to_file(str(path)):
                    index = None
            except ffms.Error:
                index = None

        if not index:
            indexer = ffms.Indexer(str(path))
            index = indexer.do_indexing(-1)
            index.write(str(cache_path))

        track_number = index.get_first_indexed_track_of_type(
            ffms.FFMS_TYPE_AUDIO
        )
        audio_source = ffms.AudioSource(str(path), track_number, index)
        self._log_api.info('audio/sampler: loaded')
        return audio_source


class AudioApi(QtCore.QObject):
    view_changed = QtCore.pyqtSignal()
    selection_changed = QtCore.pyqtSignal()
    parsed = QtCore.pyqtSignal()

    def __init__(
            self,
            media_api: 'bubblesub.api.media.media.MediaApi',
            log_api: 'bubblesub.api.log.LogApi'
    ) -> None:
        super().__init__()
        self._min = 0
        self._max = 0
        self._view_start = 0
        self._view_end = 0
        self._selection_start = 0
        self._selection_end = 0

        self._log_api = log_api
        self._media_api = media_api
        self._media_api.parsed.connect(self._on_video_parse)
        self._media_api.max_pts_changed.connect(self._on_max_pts_change)
        self._audio_source: T.Union[None, ffms.AudioSource] = None
        self._audio_source_worker = AudioSourceWorker(self, self._log_api)
        self._audio_source_worker.task_finished.connect(self._got_audio_source)

    def start(self) -> None:
        self._audio_source_worker.start()

    def stop(self) -> None:
        self._audio_source_worker.stop()

    @property
    def min(self) -> int:
        return self._min

    @property
    def max(self) -> int:
        return self._max

    @property
    def size(self) -> int:
        return self._max - self._min

    @property
    def view_start(self) -> int:
        return self._view_start

    @property
    def view_end(self) -> int:
        return self._view_end

    @property
    def view_size(self) -> int:
        return self._view_end - self._view_start

    @property
    def selection_start(self) -> int:
        return self._selection_start

    @property
    def selection_end(self) -> int:
        return self._selection_end

    @property
    def selection_size(self) -> int:
        return self._selection_end - self._selection_start

    @property
    def has_selection(self) -> bool:
        return self._selection_start != 0 or self._selection_end != 0

    @property
    def has_audio_source(self) -> bool:
        return (
            self._audio_source is not None
            and self._audio_source is not _LOADING
        )

    @property
    def channel_count(self) -> int:
        self._wait_for_audio_source()
        if not self._audio_source:
            return 0
        return T.cast(int, self._audio_source.properties.Channels)

    @property
    def bits_per_sample(self) -> int:
        self._wait_for_audio_source()
        if not self._audio_source:
            return 0
        return T.cast(int, self._audio_source.properties.BitsPerSample)

    @property
    def sample_rate(self) -> int:
        self._wait_for_audio_source()
        if not self._audio_source:
            return 0
        # other properties:
        # - BitsPerSample
        # - ChannelLayout
        # - FirstTime
        # - LastTime
        # - SampleFormat
        return T.cast(int, self._audio_source.properties.SampleRate)

    @property
    def sample_format(self) -> T.Optional[int]:
        self._wait_for_audio_source()
        if not self._audio_source:
            return None
        return T.cast(
            T.Optional[int],
            self._audio_source.properties.SampleFormat
        )

    @property
    def sample_count(self) -> int:
        self._wait_for_audio_source()
        if not self._audio_source:
            return 0
        return T.cast(int, self._audio_source.properties.NumSamples)

    def unselect(self) -> None:
        self._selection_start = 0
        self._selection_end = 0
        self.selection_changed.emit()

    def select(self, start_pts: int, end_pts: int) -> None:
        self._selection_start = self._clip(start_pts)
        self._selection_end = self._clip(end_pts)
        self.selection_changed.emit()

    def view(self, start_pts: int, end_pts: int) -> None:
        self._view_start = self._clip(start_pts)
        self._view_end = self._clip(end_pts)
        self.view_changed.emit()

    def zoom_view(self, factor: float, origin: float) -> None:
        factor = max(0.001, min(1, factor))
        old_origin = self.view_start - self._min
        old_view_size = self.view_size * origin
        self._view_start = self.min
        self._view_end = self._clip(self.min + self.size * factor)
        new_view_size = self.view_size * origin
        distance = int(old_origin - new_view_size + old_view_size)
        self.move_view(distance)  # emits view_changed

    def move_view(self, distance: int) -> None:
        view_size = self.view_size
        if self._view_start + distance < self.min:
            self.view(self.min, self.min + view_size)
        elif self._view_end + distance > self.max:
            self.view(self.max - view_size, self.max)
        else:
            self.view(self._view_start + distance, self._view_end + distance)

    def get_samples(self, start_frame: int, count: int) -> np.array:
        with _SAMPLER_LOCK:
            self._wait_for_audio_source()
            if not self._audio_source:
                return np.zeros(count).reshape(
                    (count, max(1, self.channel_count))
                )
            if start_frame + count > self.sample_count:
                count = max(0, self.sample_count - start_frame)
            if not count:
                return np.zeros(0).reshape(0, max(1, self.channel_count))
            self._audio_source.init_buffer(count)
            return self._audio_source.get_audio(start_frame)

    def save_wav(
            self,
            path_or_handle: T.Union[Path, T.IO],
            start_pts: int,
            end_pts: int
    ) -> None:
        start_frame = int(start_pts * self.sample_rate / 1000)
        end_frame = int(end_pts * self.sample_rate / 1000)
        frame_count = end_frame - start_frame

        samples = self.get_samples(start_frame, frame_count)
        # increase compatibility with external programs
        if samples.dtype.name in ('float32', 'float64'):
            samples = (samples * (1 << 31)).astype(np.int32)

        # pylint: disable=no-member
        scipy.io.wavfile.write(
            path_or_handle,
            self.sample_rate,
            samples
        )

    def _on_video_parse(self) -> None:
        self._min = 0
        self._max = 0
        self.zoom_view(1, 0.5)  # emits view_changed
        self._audio_source = _LOADING
        if self._media_api.path:
            self._audio_source_worker.schedule_task(self._media_api.path)

    def _on_max_pts_change(self) -> None:
        self._min = 0
        self._max = self._media_api.max_pts
        self.zoom_view(1, 0.5)  # emits view_changed

    def _got_audio_source(self, result: ffms.AudioSource) -> None:
        self._audio_source = result
        self.parsed.emit()

    def _wait_for_audio_source(self) -> None:
        while self._audio_source is _LOADING:
            time.sleep(0.01)

    def _clip(self, value: T.Union[int, float]) -> int:
        return max(min(self._max, int(value)), self._min)
