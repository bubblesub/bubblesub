"""GUI API."""
import typing as T

from PyQt5 import QtWidgets

import bubblesub.api.api  # pylint: disable=unused-import
import bubblesub.event

TResult = T.TypeVar('TResult')  # pylint: disable=invalid-name


class GuiApi:
    """The GUI API."""

    quit_requested = bubblesub.event.EventHandler()
    begin_update_requested = bubblesub.event.EventHandler()
    end_update_requested = bubblesub.event.EventHandler()

    def __init__(self, api: 'bubblesub.api.api.Api') -> None:
        """
        Initialize self.

        :param api: core API
        """
        super().__init__()
        self._api = api
        self._main_window: T.Optional[QtWidgets.QWidget] = None

    def set_main_window(self, main_window: QtWidgets.QWidget) -> None:
        """
        Set main window instance, needed to interact with the GUI.

        :param main_window: main window instance
        """
        self._main_window = main_window

    async def exec(
            self,
            func: T.Callable[..., T.Awaitable[TResult]],
            *args: T.Any,
            **kwargs: T.Any
    ) -> TResult:
        """
        Execute function in GUI thread.

        :param func: function to execute
        :param args: arguments passed to the function
        :param kwargs: keyword arguments passed to the function
        """
        return await func(self._api, self._main_window, *args, **kwargs)

    def quit(self) -> None:
        """Exit the application."""
        self.quit_requested.emit()

    def begin_update(self) -> None:
        """Throttle updates to GUI, reducing effects such as flickering."""
        self.begin_update_requested.emit()

    def end_update(self) -> None:
        """Stop throttling GUI updates."""
        self.end_update_requested.emit()
