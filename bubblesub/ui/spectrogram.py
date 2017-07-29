import bubblesub.util
import numpy as np
import ffms
import pyfftw


DERIVATION_SIZE = 10
DERIVATION_DISTANCE = 6


class SpectrumProviderContext(bubblesub.util.ProviderContext):
    def __init__(self, api):
        super().__init__()
        self._api = api
        self._input = pyfftw.empty_aligned(
            2 << DERIVATION_SIZE, dtype=np.float32)
        self._output = pyfftw.empty_aligned(
            (1 << DERIVATION_SIZE) + 1, dtype=np.complex64)
        self._fftw = pyfftw.FFTW(
            self._input, self._output, flags=('FFTW_MEASURE',))
        self._audio_source = None
        self._audio_path = None

    def work(self, task):
        pts = task
        self._load_audio_if_needed()

        audio_frame = int(pts * self._sample_rate / 1000.0)
        first_sample = (
            audio_frame >> DERIVATION_DISTANCE) << DERIVATION_DISTANCE
        sample_count = 2 << DERIVATION_SIZE

        samples = self._get_samples(first_sample, sample_count) / 32768.0

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
        return pts, out

    def _load_audio_if_needed(self):
        if self._audio_path != self._api.video.path:
            self._load_audio()

    def _load_audio(self):
        path = self._api.video.path
        if path and path.exists():
            self._api.log.info('audio: loading... ({})'.format(path))
            self._audio_source = ffms.AudioSource(str(path))
            self._api.log.info('audio: loaded')
        else:
            self._api.log.info('audio: not found ({})'.format(path))
            self._audio_source = None
        self._audio_path = self._api.video.path

    def _get_samples(self, start, count):
        if not self._audio_source:
            return np.zeros(count)
        if start + count > self._sample_count:
            count = self._sample_count - start
        self._audio_source.init_buffer(count)
        samples = self._audio_source.get_audio(start)
        return np.mean(samples, axis=1)

    @property
    def _sample_rate(self):
        if self._audio_source:
            return self._audio_source.properties.SampleRate
        return 0

    @property
    def _sample_count(self):
        if self._audio_source:
            return self._audio_source.properties.NumSamples
        return 0


class SpectrumProvider(bubblesub.util.Provider):
    def __init__(self, parent, api):
        self._cache = {}
        super().__init__(parent, SpectrumProviderContext(api))
