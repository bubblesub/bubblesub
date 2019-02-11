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

import asyncio
import contextlib
import functools
import typing as T
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets
from pyqtcolordialog import QColorDialog

from bubblesub.data import ROOT_DIR
from bubblesub.ui.time_edit import TimeEdit

SUBS_FILE_FILTER = "Advanced Substation Alpha (*.ass)"
VIDEO_FILE_FILTER = "Video filters (*.avi *.mkv *.webm *.mp4);;All files (*.*)"


def show_error(msg: str) -> None:
    box = QtWidgets.QMessageBox()
    box.setWindowTitle("Error")
    box.setIcon(QtWidgets.QMessageBox.Critical)
    box.setText(msg)
    box.exec_()


def show_notice(msg: str) -> None:
    box = QtWidgets.QMessageBox()
    box.setWindowTitle("Information")
    box.setIcon(QtWidgets.QMessageBox.Information)
    box.setText(msg)
    box.exec_()


def show_prompt(msg: str) -> bool:
    box = QtWidgets.QMessageBox()
    box.setWindowTitle("Question")
    box.setText(msg)
    box.setIcon(QtWidgets.QMessageBox.Question)
    box.addButton("Yes", QtWidgets.QMessageBox.YesRole)
    box.addButton("No", QtWidgets.QMessageBox.NoRole)
    return T.cast(int, box.exec_()) == 0


def blend_colors(
    color1: QtGui.QColor, color2: QtGui.QColor, ratio: float
) -> int:
    return QtGui.qRgb(
        int(color1.red() * (1 - ratio) + color2.red() * ratio),
        int(color1.green() * (1 - ratio) + color2.green() * ratio),
        int(color1.blue() * (1 - ratio) + color2.blue() * ratio),
    )


class ColorPickerPreview(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._background = QtGui.QPixmap(
            str(ROOT_DIR / "style_preview_bk" / "grid.png")
        )
        self._color = QtGui.QColor(0, 0, 0, 0)
        self.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.drawTiledPixmap(self.frameRect(), self._background)
        painter.fillRect(self.frameRect(), self._color)
        painter.end()
        super().paintEvent(event)

    def set_color(self, color: QtGui.QColor) -> None:
        self._color = color
        self.update()


class ColorPicker(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._preview = ColorPickerPreview(self)
        self._preview.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum
        )
        self._button = QtWidgets.QPushButton("Change", self)
        self._button.clicked.connect(self._on_button_click)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._preview)
        layout.addWidget(self._button)
        self._preview.setMinimumHeight(self._button.height())
        self._color = QtGui.QColor(0, 0, 0, 0)

    def _on_button_click(self, event: QtGui.QMouseEvent) -> None:
        color = QColorDialog.getColor(self._color, self)
        if color.isValid():
            self.set_color(color)

    def get_color(self) -> QtGui.QColor:
        return self._color

    def set_color(self, color: QtGui.QColor) -> None:
        if self._color != color:
            self._preview.set_color(color)
            self._color = color
            self.changed.emit()

    color = QtCore.pyqtProperty(QtGui.QColor, get_color, set_color, user=True)


async def load_dialog(
    parent: QtWidgets.QWidget,
    file_filter: str,
    directory: T.Optional[Path] = None,
) -> T.Optional[Path]:
    real_directory = (
        str(directory)
        if directory is not None
        else T.cast(str, QtCore.QDir.homePath())
    )
    dialog = QtWidgets.QFileDialog(
        parent, "Open File", directory=real_directory, filter=file_filter
    )
    dialog.setFileMode(dialog.ExistingFile)
    dialog.setAcceptMode(dialog.AcceptOpen)
    future: "asyncio.Future[T.Optional[Path]]" = asyncio.Future()

    def on_accept() -> None:
        future.set_result(Path(dialog.selectedFiles()[0]))

    def on_reject() -> None:
        future.set_result(None)

    dialog.accepted.connect(on_accept)
    dialog.rejected.connect(on_reject)
    dialog.open()
    return await future


async def save_dialog(
    parent: QtWidgets.QWidget,
    file_filter: T.Optional[str],
    directory: T.Optional[Path] = None,
    file_name: T.Optional[str] = None,
) -> T.Optional[Path]:
    real_directory = (
        str(directory)
        if directory is not None
        else T.cast(str, QtCore.QDir.homePath())
    )
    if file_name:
        real_directory += "/" + file_name

    dialog = QtWidgets.QFileDialog(
        parent,
        "Save File",
        directory=real_directory,
        filter=file_filter or "Any File (*)",
    )
    dialog.setFileMode(dialog.AnyFile)
    dialog.setAcceptMode(dialog.AcceptSave)
    future: "asyncio.Future[T.Optional[Path]]" = asyncio.Future()

    def on_accept() -> None:
        future.set_result(Path(dialog.selectedFiles()[0]))

    def on_reject() -> None:
        future.set_result(None)

    dialog.accepted.connect(on_accept)
    dialog.rejected.connect(on_reject)
    dialog.open()
    return await future


async def time_jump_dialog(
    parent: QtWidgets.QWidget,
    value: int = 0,
    relative_label: str = "Time:",
    absolute_label: str = "Time:",
    relative_checked: bool = True,
    show_radio: bool = True,
) -> T.Optional[T.Tuple[int, bool]]:
    class TimeJumpDialog(QtWidgets.QDialog):
        def __init__(self, parent: QtWidgets.QWidget = None) -> None:
            super().__init__(parent)
            self.setWindowTitle("Select time...")

            self._label = QtWidgets.QLabel("", self)
            self._time_edit = TimeEdit(self)
            self._radio_rel = QtWidgets.QRadioButton("Relative", self)
            self._radio_abs = QtWidgets.QRadioButton("Absolute", self)
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
            return (self._time_edit.get_value(), self._radio_rel.isChecked())

    future: "asyncio.Future[T.Optional[T.Tuple[int, bool]]]" = asyncio.Future()
    dialog = TimeJumpDialog(parent)

    def on_accept() -> None:
        future.set_result(dialog.value())

    def on_reject() -> None:
        future.set_result(None)

    dialog.accepted.connect(on_accept)
    dialog.rejected.connect(on_reject)
    dialog.open()
    return await future


def get_text_edit_row_height(
    editor: QtWidgets.QPlainTextEdit, rows: int
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


class ImmediateDataWidgetMapper(QtCore.QObject):
    def __init__(
        self,
        model: QtCore.QAbstractItemModel,
        signal_map: T.Optional[T.Dict[QtWidgets.QWidget, str]] = None,
        submit_wrapper: T.Optional[
            T.Callable[[], T.ContextManager[None]]
        ] = None,
    ) -> None:
        super().__init__()
        self._model = model
        self._mappings: T.List[T.Tuple[QtWidgets.QWidget, int]] = []
        self._row_idx: T.Optional[int] = None
        self._item_delegate = QtWidgets.QItemDelegate(self)
        self._submit_wrapper: T.Callable[
            [], T.ContextManager[None]
        ] = submit_wrapper or contextlib.nullcontext

        self._signal_map: T.Dict[QtWidgets.QWidget, str] = {
            QtWidgets.QCheckBox: "clicked",
            QtWidgets.QSpinBox: "valueChanged",
            QtWidgets.QDoubleSpinBox: "valueChanged",
            QtWidgets.QComboBox: "currentTextChanged",
            ColorPicker: "changed",
            TimeEdit: "value_changed",
        }
        if signal_map:
            self._signal_map.update(signal_map)

        model.dataChanged.connect(self._model_data_change)

    def add_mapping(self, widget: QtWidgets.QWidget, idx: int) -> None:
        for type_, signal_name in self._signal_map.items():
            if isinstance(widget, type_):
                signal = getattr(widget, signal_name)
                signal.connect(
                    functools.partial(self._widget_data_change, idx)
                )
                self._mappings.append((widget, idx))
                return
        raise RuntimeError(f'unknown widget type: "{type(widget)}"')

    def set_current_index(self, row_idx: T.Optional[int]) -> None:
        self._row_idx = row_idx
        for widget, col_idx in self._mappings:
            self._write_to_widget(widget, row_idx, col_idx)

    def _widget_data_change(self, sender_col_idx: int) -> None:
        if self._row_idx is None:
            return
        for widget, col_idx in self._mappings:
            if sender_col_idx == col_idx:
                self._write_to_model(widget, self._row_idx, col_idx)

    def _model_data_change(
        self, top_left: QtCore.QModelIndex, bottom_right: QtCore.QModelIndex
    ) -> None:
        if self._row_idx is None:
            return
        for widget, col_idx in self._mappings:
            if (
                top_left.row() <= self._row_idx <= bottom_right.row()
                and top_left.column() <= col_idx <= bottom_right.column()
            ):
                self._write_to_widget(widget, self._row_idx, col_idx)

    def _write_to_widget(
        self, widget: QtWidgets.QWidget, row_idx: T.Optional[int], col_idx: int
    ) -> None:
        name = widget.metaObject().userProperty().name()
        cur_value = (
            QtCore.QVariant()
            if row_idx is None
            else self._model.index(row_idx, col_idx).data(QtCore.Qt.EditRole)
        )
        prev_value = widget.property(name)
        if cur_value != prev_value:
            widget.setProperty(name, cur_value)
            if isinstance(widget, QtWidgets.QComboBox) and row_idx is not None:
                cb_row_idx = widget.findText(cur_value)
                widget.setCurrentIndex(cb_row_idx)

    def _write_to_model(
        self, widget: QtWidgets.QWidget, row_idx: int, col_idx: int
    ) -> None:
        name = widget.metaObject().userProperty().name()
        cur_value = widget.property(name)
        prev_value = self._model.data(
            self._model.index(row_idx, col_idx), QtCore.Qt.EditRole
        )
        if cur_value != prev_value:
            with self._submit_wrapper():
                self._model.setData(
                    self._model.index(row_idx, col_idx),
                    cur_value,
                    QtCore.Qt.EditRole,
                )
