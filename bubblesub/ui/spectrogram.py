import queue
from PyQt5 import QtCore
import numpy as np
import ffms
import pyfftw
from bubblesub.ui.util import SimpleThread


HORIZONTAL_RES = 10
DERIVATION_SIZE = 10
DERIVATION_DISTANCE = 6


class SpectrogramThread(SimpleThread):
    def __init__(self, queue, callback, api):
        super().__init__(queue, callback)
        self._api = api

        self._input = pyfftw.empty_aligned(
            2 << DERIVATION_SIZE, dtype=np.float32)
        self._output = pyfftw.empty_aligned(
            (1 << DERIVATION_SIZE) + 1, dtype=np.complex64)
        self._fftw = pyfftw.FFTW(
            self._input, self._output, flags=('FFTW_MEASURE',))

        self._audio_source = None

    def start_work(self):
        path = self._api.video.path
        if path and path.exists():
            self._api.log('audio: loading... ({})'.format(path))
            self._audio_source = ffms.AudioSource(str(path))
            self._api.log('audio: loaded')
        else:
            self._api.log('audio: not found ({})'.format(path))
            self._audio_source = None

    # TODO: something's wrong with it...
    def work(self, block_idx):
        pts = block_idx * HORIZONTAL_RES
        audio_frame = int(pts * self._sample_rate / 1000.0)
        first_sample = (
            audio_frame >> DERIVATION_DISTANCE) << DERIVATION_DISTANCE
        sample_count = 2 << DERIVATION_SIZE

        samples = self._get_samples(first_sample, sample_count)
        # samples = np.random.random(sample_count)

        samples /= 32768.0
        self._input[:] = samples
        out = self._fftw()

        scale_factor = 9 / np.sqrt(1 * (1 << DERIVATION_SIZE))
        out = np.log(
            np.sqrt(
                np.real(out) * np.real(out)
                + np.imag(out) * np.imag(out)
            ) * scale_factor + 1)

        out *= 255
        out = np.clip(out, 0, 255)
        out = np.flip(out, axis=0)
        out = out.astype(dtype=np.uint8)
        return block_idx, out

    @property
    def _sample_rate(self):
        if self._audio_source:
            return self._audio_source.properties.SampleRate
        return 0

    @property
    def _channel_count(self):
        if self._audio_source:
            return self._audio_source.properties.Channels
        return 0

    @property
    def _sample_count(self):
        if self._audio_source:
            return self._audio_source.properties.NumSamples
        return 0

    def _get_samples(self, start, count):
        if not self._audio_source:
            return np.zeros(count)
        if start + count > self._sample_count:
            count = self._sample_count - start
        self._audio_source.init_buffer(count)
        samples = self._audio_source.get_audio(start)
        return np.mean(samples.reshape(self._channel_count, -1), axis=0)


class SpectrumProvider(QtCore.QObject):
    updated = QtCore.pyqtSignal()

    def __init__(self, api):
        super().__init__()
        self._api = api
        self._cache = {}
        self._queue = queue.LifoQueue()

        # TODO: handle video source changes
        self._worker = SpectrogramThread(
            self._queue, self._fft_rendering_finished, self._api)
        self._worker.start()

    def get_fft(self, pts):
        block_idx = pts // HORIZONTAL_RES
        if block_idx in self._cache:
            return self._cache[block_idx]
        self._queue.put(block_idx)
        return None

    def _fft_rendering_finished(self, result):
        block_idx, out = result.value
        self._cache[block_idx] = out
        self.updated.emit()
