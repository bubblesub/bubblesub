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

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.util import ms_to_str, str_to_ms


class _TimeLineEdit(QtWidgets.QLineEdit):
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        super().keyPressEvent(event)

        if not event.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
            return

        value = self.parent().get_value()
        delta = 10
        if event.key() == QtCore.Qt.Key_Up:
            value += delta
        elif event.key() == QtCore.Qt.Key_Down:
            value -= delta

        self.parent().set_value(value)


class TimeEdit(QtWidgets.QWidget):
    value_changed = QtCore.pyqtSignal(int)

    def __init__(
        self,
        parent: QtWidgets.QWidget = None,
        allow_negative: bool = False,
        **kwargs: T.Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._value = 0
        self._allow_negative = False

        self._edit = _TimeLineEdit(self)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._edit)

        self._edit.textEdited.connect(self._on_text_edit)

        self._reset_mask()
        self._reset_text()

    def _on_text_edit(self, text: str) -> None:
        self._qt_value = str_to_ms(text)

    def set_allow_negative(self, allow: bool) -> None:
        self._allow_negative = allow
        self._qt_value = 0
        self._reset_mask()
        self._reset_text()

    @QtCore.pyqtProperty(int, user=True)
    def _qt_value(self, user=True) -> int:
        return self._value

    @_qt_value.setter
    def _qt_value(self, value: int) -> None:
        if value != self._value:
            self._value = value
            text = ms_to_str(value)
            if self._allow_negative and value >= 0:
                text = "+" + text
            if text != self._edit.text():
                self._edit.setText(text)
                self._edit.setCursorPosition(0)
            self.value_changed.emit(self._value)

    def get_value(self) -> int:
        return self._qt_value

    def set_value(self, time: int) -> None:
        self._qt_value = time

    def _reset_mask(self) -> None:
        if self._allow_negative:
            self._edit.setInputMask("X99:99:99.999")
            self._edit.setValidator(
                QtGui.QRegExpValidator(
                    QtCore.QRegExp(r"[+-]\d\d:\d\d:\d\d\.\d\d\d"),
                    self.parent(),
                )
            )
        else:
            self._edit.setInputMask("99:99:99.999")

    def _reset_text(self) -> None:
        if self._allow_negative:
            self._edit.setText("+00:00:00.000")
        else:
            self._edit.setText("00:00:00.000")
        self._edit.setCursorPosition(0)
