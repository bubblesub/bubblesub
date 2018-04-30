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

"""Event handler and signaling."""

import typing as T

from PyQt5 import QtCore


class EventHandler:
    """Event handler."""

    def __init__(self, *types: T.Any) -> None:
        """
        Initialize self.

        :param types: types of arguments for the subscriber callbacks
        """
        class _SignalWrapper(QtCore.QObject):
            signal = QtCore.pyqtSignal(types)

        self._signal_wrapper = _SignalWrapper()

    def emit(self, *args: T.Any) -> None:
        """
        Emit signal for the subscribers to consume.

        :param args: signal arguments
        """
        self._signal.emit(*args)

    def connect(self, handler: T.Callable) -> None:
        """
        Attach a new subscriber callback to the signal.

        :param handler: subscriber callback
        """
        self._signal.connect(handler)

    def disconnect(self, handler: T.Callable) -> None:
        """
        Detach a subscriber callback from the signal.

        :param handler: subscriber callback
        """
        self._signal.disconnect(handler)

    @property
    def _signal(self) -> QtCore.pyqtSignal:
        return self._signal_wrapper.signal
