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

"""ASS file metadata."""

import typing as T
from collections import OrderedDict

from PyQt5 import QtCore


class AssMeta(QtCore.QObject):
    """ASS file metadata."""

    changed = QtCore.pyqtSignal()

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__()
        self._data: T.Dict[str, str] = OrderedDict()

    def clear(self) -> None:
        """Clear self."""
        self._data.clear()
        self.changed.emit()

    def update(self, new_content: T.Mapping[str, str]) -> None:
        """
        Update self with new content.

        :param new_content: content to update with
        """
        if self._data != new_content:
            self._data.update(new_content)
            self.changed.emit()

    def get(self, key: str, fallback: T.Any = None) -> T.Optional[str]:
        """
        Get value under given key.

        :param key: key to look up the value for
        :param fallback: what to return if the value is not found
        :return: value associated with the given key or the fallback value
        """
        return self._data.get(key, fallback)

    def set(self, key: str, value: str) -> None:
        """
        Set value under given key.

        :param key: key to set the value for
        :param value: the new value
        """
        if self._data.get(key, None) != value:
            self._data[key] = value
            self.changed.emit()

    def remove(self, key: str) -> None:
        """
        Remove the specified key.

        :param key: key to remove
        """
        if key in self._data:
            del self._data[key]
            self.changed.emit()

    def items(self) -> T.ItemsView[str, str]:
        """
        Return contents as key-value tuples.

        :return: list of key-value tuples
        """
        return self._data.items()
