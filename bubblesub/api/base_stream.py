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

"""Common class for audio and video streams."""

import uuid
from pathlib import Path
from typing import ClassVar

from PyQt5.QtCore import pyqtBoundSignal

from bubblesub.errors import ResourceUnavailable


class StreamUnavailable(ResourceUnavailable):
    """Exception raised when trying to access audio or video stream properties
    when the stream is not fully loaded yet.
    """


class BaseStream:
    """Base stream."""

    uid: uuid.UUID
    loaded: ClassVar[pyqtBoundSignal]
    changed: ClassVar[pyqtBoundSignal]
    errored: ClassVar[pyqtBoundSignal]

    @property
    def path(self) -> Path:
        """Return stream source path.

        :return: path
        """
        raise NotImplementedError("not implemented")
