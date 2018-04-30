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

import typing as T

import ffms
import pyfftw
import numpy as np

import bubblesub.api
import bubblesub.worker


DERIVATION_SIZE = 10
DERIVATION_DISTANCE = 6


class SpectrumWorker(bubblesub.worker.Worker):
    def __init__(self, api: bubblesub.api.Api) -> None:
        super().__init__()
        self._api = api
        self._input: T.Any = None
        self._output: T.Any = None
        self._fftw: T.Any = None

    def _start_work(self) -> None:
        self._input = pyfftw.empty_aligned(
            2 << DERIVATION_SIZE, dtype=np.float32
        )
        self._output = pyfftw.empty_aligned(
            (1 << DERIVATION_SIZE) + 1, dtype=np.complex64
        )
        self._fftw = pyfftw.FFTW(
            self._input, self._output, flags=('FFTW_MEASURE',)
        )

    def _do_work(self, task: T.Any) -> T.Any:
        pts = task

        audio_frame = int(pts * self._api.media.audio.sample_rate / 1000.0)
        first_sample = (
            audio_frame >> DERIVATION_DISTANCE
        ) << DERIVATION_DISTANCE
        sample_count = 2 << DERIVATION_SIZE

        samples = self._api.media.audio.get_samples(first_sample, sample_count)
        samples = np.mean(samples, axis=1)
        sample_fmt = self._api.media.audio.sample_format
        if sample_fmt is None:
            return (pts, np.zeros((1 << DERIVATION_SIZE) + 1))
        elif sample_fmt == ffms.FFMS_FMT_S16:
            samples /= 32768.
        elif sample_fmt == ffms.FFMS_FMT_S32:
            samples /= 4294967296.
        elif sample_fmt not in (ffms.FFMS_FMT_FLT, ffms.FFMS_FMT_DBL):
            raise RuntimeError('Unknown sample format: {}'.format(sample_fmt))

        assert self._input is not None
        self._input[0:len(samples)] = samples

        assert self._fftw is not None
        out = self._fftw()

        scale_factor = 9 / np.sqrt(1 * (1 << DERIVATION_SIZE))
        out = np.log(
            np.sqrt(
                np.real(out) * np.real(out)
                + np.imag(out) * np.imag(out)
            ) * scale_factor + 1
        )

        out *= 255
        out = np.clip(out, 0, 255)
        out = np.flip(out, axis=0)
        out = out.astype(dtype=np.uint8)
        return (pts, out)
