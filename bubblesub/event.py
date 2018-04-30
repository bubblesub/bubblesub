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
