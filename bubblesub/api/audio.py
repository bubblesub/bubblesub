import time
import threading
import wave
import bubblesub.util
import ffms
import scipy.io.wavfile
import numpy as np
from PyQt5 import QtCore


_LOADING = object()
_SAMPLER_LOCK = threading.Lock()


class AudioSourceProviderContext(bubblesub.util.ProviderContext):
    def __init__(self, log_api):
        super().__init__()
        self._log_api = log_api

    def work(self, task):
        path = task
        self._log_api.info('audio/sampler: loading... ({})'.format(path))
        audio_source = ffms.AudioSource(str(path))
        self._log_api.info('audio/sampler: loaded')
        return audio_source


class AudioSourceProvider(bubblesub.util.Provider):
    def __init__(self, parent, log_api):
        super().__init__(parent, AudioSourceProviderContext(log_api))


class AudioApi(QtCore.QObject):
    view_changed = QtCore.pyqtSignal()
    selection_changed = QtCore.pyqtSignal()
    parsed = QtCore.pyqtSignal()

    def __init__(self, video_api, log_api):
        super().__init__()
        self._min = 0
        self._max = 0
        self._view_start = 0
        self._view_end = 0
        self._selection_start = None
        self._selection_end = None

        self._log_api = log_api
        self._video_api = video_api
        self._video_api.parsed.connect(self._video_parsed)
        self._audio_source = None
        self._audio_source_provider = AudioSourceProvider(self, self._log_api)
        self._audio_source_provider.finished.connect(self._got_audio_source)

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def size(self):
        return self._max - self._min

    @property
    def view_start(self):
        return self._view_start

    @property
    def view_end(self):
        return self._view_end

    @property
    def view_size(self):
        return self._view_end - self._view_start

    @property
    def selection_start(self):
        return self._selection_start

    @property
    def selection_end(self):
        return self._selection_end

    @property
    def has_selection(self):
        return not (
            self._selection_start is None or self._selection_end is None)

    @property
    def selection_size(self):
        if not self.has_selection:
            return 0
        return self._selection_end - self._selection_start

    @property
    def has_audio_source(self):
        return self._audio_source and self._audio_source is not _LOADING

    @property
    def channel_count(self):
        self._wait_for_audio_source()
        if not self._audio_source:
            return 0
        return self._audio_source.properties.Channels

    @property
    def bits_per_sample(self):
        self._wait_for_audio_source()
        if not self._audio_source:
            return 0
        return self._audio_source.properties.BitsPerSample

    @property
    def sample_rate(self):
        self._wait_for_audio_source()
        if not self._audio_source:
            return 0
        # other properties:
        # - BitsPerSample
        # - ChannelLayout
        # - FirstTime
        # - LastTime
        # - SampleFormat
        return self._audio_source.properties.SampleRate

    @property
    def sample_format(self):
        self._wait_for_audio_source()
        if not self._audio_source:
            return None
        return self._audio_source.properties.SampleFormat

    @property
    def sample_count(self):
        self._wait_for_audio_source()
        if not self._audio_source:
            return 0
        return self._audio_source.properties.NumSamples

    def unselect(self):
        self._selection_start = None
        self._selection_end = None
        self.selection_changed.emit()

    def select(self, start_pts, end_pts):
        self._selection_start = self._clip(start_pts)
        self._selection_end = self._clip(end_pts)
        self.selection_changed.emit()

    def view(self, start_pts, end_pts):
        self._view_start = self._clip(start_pts)
        self._view_end = self._clip(end_pts)
        self.view_changed.emit()

    def zoom_view(self, factor):
        factor = max(0.001, min(1, factor))
        old_origin = self.view_start - self._min
        old_view_size = self.view_size / 2
        self._view_start = self.min
        self._view_end = self._clip(self.min + self.size * factor)
        new_view_size = self.view_size / 2
        distance = old_origin - new_view_size + old_view_size
        self.move_view(distance)  # emits view_changed

    def move_view(self, distance):
        view_size = self.view_size
        if self._view_start + distance < self.min:
            self.view(self.min, self.min + view_size)
        elif self._view_end + distance > self.max:
            self.view(self.max - view_size, self.max)
        else:
            self.view(self._view_start + distance, self._view_end + distance)

    def get_samples(self, start_frame, count):
        with _SAMPLER_LOCK:
            self._wait_for_audio_source()
            if not self._audio_source:
                return np.zeros(count).reshape(
                    (count, max(1, self.channel_count)))
            if start_frame + count > self.sample_count:
                count = self.sample_count - start_frame
            self._audio_source.init_buffer(count)
            return self._audio_source.get_audio(start_frame)

    def save_wav(self, path_or_handle, start_pts, end_pts):
        start_frame = int(start_pts * self.sample_rate / 1000)
        end_frame = int(end_pts * self.sample_rate / 1000)
        frame_count = end_frame - start_frame

        samples = self.get_samples(start_frame, frame_count)
        scipy.io.wavfile.write(path_or_handle, self.sample_rate, samples)

    def _set_max_pts(self, max_pts):
        self._min = 0
        self._max = max_pts
        self.zoom_view(1)  # emits view_changed

    def _video_parsed(self):
        self._set_max_pts(self._video_api.max_pts)
        self._audio_source = _LOADING
        if self._video_api.path:
            self._audio_source_provider.schedule(self._video_api.path)

    def _got_audio_source(self, result):
        self._audio_source = result
        self.parsed.emit()

    def _wait_for_audio_source(self):
        while self._audio_source is _LOADING:
            time.sleep(0.01)

    def _clip(self, value):
        return max(min(self._max, value), self._min)
