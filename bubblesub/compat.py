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

"""Compatibility with Python 3.6."""

import typing as T

try:
    from contextlib import nullcontext  # pylint: disable=unused-import
except ImportError:
    from contextlib import contextmanager

    @contextmanager
    def nullcontext(data: T.Any) -> T.Any:
        """Emulated Python 3.6 variant of Python 3.7's nullcontext.

        :param data: data to return
        """
        yield data
