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

import functools
import typing as T
from pathlib import Path

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.util


def error(msg: str) -> None:
    box = QtWidgets.QMessageBox()
    box.setWindowTitle('Error')
    box.setIcon(QtWidgets.QMessageBox.Critical)
    box.setText(msg)
    box.exec_()


def notice(msg: str) -> None:
    box = QtWidgets.QMessageBox()
    box.setWindowTitle('Information')
    box.setIcon(QtWidgets.QMessageBox.Information)
    box.setText(msg)
    box.exec_()


def ask(msg: str) -> bool:
    box = QtWidgets.QMessageBox()
    box.setWindowTitle('Question')
    box.setText(msg)
    box.setIcon(QtWidgets.QMessageBox.Question)
    box.addButton('Yes', QtWidgets.QMessageBox.YesRole)
    box.addButton('No', QtWidgets.QMessageBox.NoRole)
    return T.cast(int, box.exec_()) == 0


def blend_colors(
        color1: QtGui.QColor,
        color2: QtGui.QColor,
        ratio: float
) -> int:
    return QtGui.qRgb(
        int(color1.red() * (1 - ratio) + color2.red() * ratio),
        int(color1.green() * (1 - ratio) + color2.green() * ratio),
        int(color1.blue() * (1 - ratio) + color2.blue() * ratio)
    )


class ColorPicker(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._label = QtWidgets.QLabel(self)
        self._label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum
        )
        self._button = QtWidgets.QPushButton('Change', self)
        self._button.clicked.connect(self._on_button_click)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)
        layout.addWidget(self._button)
        self._label.setMinimumHeight(self._button.height())
        self._color = QtGui.QColor(0, 0, 0, 0)
        self.set_color(self._color)

    def _on_button_click(self, _event: QtGui.QMouseEvent) -> None:
        dialog = QtWidgets.QColorDialog(self)
        dialog.setCurrentColor(self._color)
        dialog.setOption(dialog.ShowAlphaChannel, True)
        if dialog.exec_():
            self.set_color(dialog.selectedColor())

    def get_color(self) -> QtGui.QColor:
        return self._color

    def set_color(self, color: QtGui.QColor) -> None:
        style = '''QLabel:enabled {{
            background-color: #{:02x}{:02x}{:02x};
            opacity: {};
            border: 1px solid black;
        }}'''.format(color.red(), color.green(), color.blue(), color.alpha())
        self._label.setStyleSheet(style)
        if self._color != color:
            self._color = color
            self.changed.emit()

    color = QtCore.pyqtProperty(QtGui.QColor, get_color, set_color, user=True)


class TimeEdit(QtWidgets.QLineEdit):
    def __init__(
            self,
            parent: QtWidgets.QWidget = None,
            allow_negative: bool = False
    ) -> None:
        super().__init__(parent)
        self._allow_negative = False
        self.set_allow_negative(allow_negative)

    def set_allow_negative(self, allow: bool) -> None:
        self._allow_negative = allow
        if allow:
            self.setInputMask('X99:99:99.999')
            self.setValidator(
                QtGui.QRegExpValidator(
                    QtCore.QRegExp(r'[+-]\d\d:\d\d:\d\d\.\d\d\d'),
                    self.parent()
                )
            )
        else:
            self.setInputMask('99:99:99.999')
        self.reset_text()

    def reset_text(self) -> None:
        if self._allow_negative:
            self.setText('+00:00:00.000')
        else:
            self.setText('00:00:00.000')
        self.setCursorPosition(0)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        super().keyPressEvent(event)

        if not event.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
            return

        value = self.get_value()
        delta = 10
        if event.key() == QtCore.Qt.Key_Up:
            value += delta
        elif event.key() == QtCore.Qt.Key_Down:
            value -= delta

        self.set_value(value)

    def get_value(self) -> int:
        return bubblesub.util.str_to_ms(self.text())

    def set_value(self, time: int) -> None:
        text = bubblesub.util.ms_to_str(time)
        if self._allow_negative and time >= 0:
            text = '+' + text
        self.setText(text)
        self.textEdited.emit(self.text())
        self.setCursorPosition(0)


@functools.lru_cache(maxsize=None)
def get_color(api: bubblesub.api.Api, color_name: str) -> QtGui.QColor:
    current_palette = api.opt.general.gui.current_palette
    try:
        palette_def = api.opt.general.gui.palettes[current_palette]
    except KeyError:
        return QtGui.QVariant()
    color_value = palette_def[color_name]
    return QtGui.QColor(*color_value)


def load_dialog(
        parent: QtWidgets.QWidget,
        file_filter: str,
        directory: T.Optional[Path] = None
) -> T.Optional[Path]:
    path, _ = QtWidgets.QFileDialog.getOpenFileName(
        parent,
        directory=(
            str(directory)
            if directory is not None else
            T.cast(str, QtCore.QDir.homePath())
        ),
        filter=file_filter
    )
    return Path(path) if path else None


def save_dialog(
        parent: QtWidgets.QWidget,
        file_filter: T.Optional[str],
        directory: T.Optional[Path] = None,
        file_name: T.Optional[str] = None
) -> T.Optional[Path]:
    real_directory = (
        str(directory)
        if directory is not None else
        T.cast(str, QtCore.QDir.homePath())
    )
    if file_name:
        real_directory += '/' + file_name
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent,
        directory=real_directory,
        filter=file_filter or 'Any file (*)'
    )
    return Path(path) if path else None


def time_jump_dialog(
        parent: QtWidgets.QWidget,
        value: int = 0,
        relative_label: str = 'Time:',
        absolute_label: str = 'Time:',
        relative_checked: bool = True,
        show_radio: bool = True
) -> T.Optional[T.Tuple[int, bool]]:
    class TimeJumpDialog(QtWidgets.QDialog):
        def __init__(self, parent: QtWidgets.QWidget = None) -> None:
            super().__init__(parent)
            self.setWindowTitle('Select time...')

            self._label = QtWidgets.QLabel('', self)
            self._time_edit = TimeEdit(self)
            self._radio_rel = QtWidgets.QRadioButton('Relative', self)
            self._radio_abs = QtWidgets.QRadioButton('Absolute', self)
            if relative_checked:
                self._radio_rel.setChecked(True)
            else:
                self._radio_abs.setChecked(True)
            strip = QtWidgets.QDialogButtonBox(self)
            strip.addButton(strip.Ok)
            strip.addButton(strip.Cancel)

            if not show_radio:
                self._radio_abs.setHidden(True)
                self._radio_rel.setHidden(True)

            strip.accepted.connect(self.accept)
            strip.rejected.connect(self.reject)
            self._radio_rel.clicked.connect(self._on_radio_click)
            self._radio_abs.clicked.connect(self._on_radio_click)

            layout = QtWidgets.QVBoxLayout(self)
            layout.addWidget(self._label)
            layout.addWidget(self._time_edit)
            layout.addWidget(self._radio_rel)
            layout.addWidget(self._radio_abs)
            layout.addWidget(strip)

            self._on_radio_click()
            self._time_edit.set_value(value)

        def _on_radio_click(self) -> None:
            is_relative = self._radio_rel.isChecked()
            if is_relative:
                self._label.setText(relative_label)
            else:
                self._label.setText(absolute_label)
            self._time_edit.set_allow_negative(is_relative)

        def value(self) -> T.Tuple[int, bool]:
            return (
                self._time_edit.get_value(),
                self._radio_rel.isChecked()
            )

    dialog = TimeJumpDialog(parent)
    if dialog.exec_():
        return dialog.value()
    return None


def get_text_edit_row_height(
        editor: QtWidgets.QPlainTextEdit,
        rows: int
) -> int:
    metrics = QtGui.QFontMetrics(editor.document().defaultFont())
    margins = editor.contentsMargins()
    return (
        metrics.lineSpacing() * rows
        + (editor.document().documentMargin() + editor.frameWidth()) * 2
        + margins.top()
        + margins.bottom()
        + 1
    )
