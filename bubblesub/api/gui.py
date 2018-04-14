import typing as T

from PyQt5 import QtCore
from PyQt5 import QtWidgets

import bubblesub.api.api  # pylint: disable=unused-import

TResult = T.TypeVar('TResult')  # pylint: disable=invalid-name


class GuiApi(QtCore.QObject):
    quit_requested = QtCore.pyqtSignal()
    begin_update_requested = QtCore.pyqtSignal()
    end_update_requested = QtCore.pyqtSignal()

    def __init__(self, api: 'bubblesub.api.api.Api') -> None:
        super().__init__()
        self._api = api
        self._main_window: T.Optional[QtWidgets.QWidget] = None

    def set_main_window(self, main_window: QtWidgets.QWidget) -> None:
        self._main_window = main_window

    async def exec(
            self,
            func: T.Callable[..., T.Awaitable[TResult]],
            *args: T.Any,
            **kwargs: T.Any
    ) -> TResult:
        return await func(self._api, self._main_window, *args, **kwargs)

    def quit(self) -> None:
        self.quit_requested.emit()

    def begin_update(self) -> None:
        self.begin_update_requested.emit()

    def end_update(self) -> None:
        self.end_update_requested.emit()
