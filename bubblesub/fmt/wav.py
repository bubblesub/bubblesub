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

# Copyright (c) 2001, 2002 Enthought, Inc.
# All rights reserved.
#
# Copyright (c) 2003-2017 SciPy Developers.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   a. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#   b. Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#   c. Neither the name of Enthought nor the names of the SciPy Developers
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.

"""WAV file reader."""

import struct
import sys
from typing import IO

import numpy as np

WAVE_FORMAT_PCM = 0x0001
WAVE_FORMAT_IEEE_FLOAT = 0x0003


def write_wav(handle: IO[bytes], rate: int, data: np.array) -> None:
    """Write a numpy array of samples as a single uncompressed WAV file.

    To write multiple-channels, use a 2-D array of shape (Nsamples, Nchannels).
    The bits-per-sample and PCM/float will be determined by the data-type.

    :param handle: handle to write the file to
    :param rate: the sample rate in samples/sec
    :param data: a 1D or 2D numpy array of either integer or float data-type
    """
    dkind = data.dtype.kind

    if not (
        dkind == "i"
        or dkind == "f"
        or (dkind == "u" and data.dtype.itemsize == 1)
    ):
        raise ValueError(f"unsupported data type {data.dtype!r}")

    header_data = b"RIFF"
    header_data += b"\x00\x00\x00\x00"
    header_data += b"WAVE"

    # fmt chunk
    header_data += b"fmt "
    if dkind == "f":
        format_tag = WAVE_FORMAT_IEEE_FLOAT
    else:
        format_tag = WAVE_FORMAT_PCM
    if data.ndim == 1:
        channels = 1
    else:
        channels = data.shape[1]

    bit_depth = data.dtype.itemsize * 8
    bytes_per_second = rate * (bit_depth // 8) * channels
    block_align = channels * (bit_depth // 8)

    fmt_chunk_data = struct.pack(
        "<HHIIHH",
        format_tag,
        channels,
        rate,
        bytes_per_second,
        block_align,
        bit_depth,
    )
    if dkind not in "iu":
        # add cbSize field for non-PCM files
        fmt_chunk_data += b"\x00\x00"

    header_data += struct.pack("<I", len(fmt_chunk_data))
    header_data += fmt_chunk_data

    # fact chunk (non-PCM files)
    if dkind not in "iu":
        header_data += b"fact"
        header_data += struct.pack("<II", 4, data.shape[0])

    # check data size (needs to be immediately before the data chunk)
    if ((len(header_data) - 4 - 4) + (4 + 4 + data.nbytes)) > 0xFFFFFFFF:
        raise ValueError("data exceeds wave file size limit")

    handle.write(header_data)
    handle.write(b"data")
    handle.write(struct.pack("<I", data.nbytes))
    if data.dtype.byteorder == ">" or (
        data.dtype.byteorder == "=" and sys.byteorder == "big"
    ):
        data = data.byteswap()
    handle.write(data.ravel().view("b").data)

    # Determine file size and place it at start of the file.
    size = handle.tell()
    handle.seek(4)
    handle.write(struct.pack("<I", size - 8))
