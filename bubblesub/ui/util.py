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
from collections.abc import Callable
from functools import partial, wraps
from pathlib import Path
from typing import Any, Optional, cast

from PyQt5.QtCore import (
    QAbstractItemModel,
    QDir,
    QModelIndex,
    QObject,
    Qt,
    QVariant,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from PyQt5.QtGui import (
    QColor,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPixmap,
    qRgb,
)
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QItemDelegate,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from pyqtcolordialog import QColorDialog

from bubblesub.ui.assets import ASSETS_DIR
from bubblesub.ui.time_edit import TimeEdit

SUBS_FILE_FILTER = "Advanced Substation Alpha (*.ass)"
VIDEO_FILE_FILTER = "Video filters (*.avi *.mkv *.webm *.mp4);;All files (*.*)"
AUDIO_FILE_FILTER = (
    "Audio filters (*.wav *.mp3 *.flac *.avi *.mkv *.webm *.mp4);;"
    "All files (*.*)"
)


def async_slot(*args: Any) -> Callable[..., Callable[..., None]]:
    def _outer(
        func: Callable[..., asyncio.Future[Any]]
    ) -> Callable[..., None]:
        @pyqtSlot(*args)
        @wraps(func)
        def _inner(*args: Any, **kwargs: Any) -> None:
            asyncio.ensure_future(func(*args, **kwargs))

        return _inner

    return _outer


def async_dialog_exec(dialog: QDialog) -> Any:
    future: "asyncio.Future" = asyncio.Future()
    dialog.finished.connect(future.set_result)
    dialog.open()
    return future


async def show_error(msg: str, parent: QWidget) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle("Error")
    box.setIcon(QMessageBox.Critical)
    box.setText(msg)
    await async_dialog_exec(box)


async def show_notice(msg: str, parent: QWidget) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle("Information")
    box.setIcon(QMessageBox.Information)
    box.setText(msg)
    await async_dialog_exec(box)


async def show_prompt(msg: str, parent: QWidget) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle("Question")
    box.setText(msg)
    box.setIcon(QMessageBox.Question)
    box.addButton("Yes", QMessageBox.YesRole)
    box.addButton("No", QMessageBox.NoRole)
    return await async_dialog_exec(box) == 0


def blend_colors(color1: QColor, color2: QColor, ratio: float) -> int:
    return qRgb(
        int(color1.red() * (1 - ratio) + color2.red() * ratio),
        int(color1.green() * (1 - ratio) + color2.green() * ratio),
        int(color1.blue() * (1 - ratio) + color2.blue() * ratio),
    )


class ColorPickerPreview(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._background = QPixmap(
            str(ASSETS_DIR / "style_preview_bk" / "grid.png")
        )
        self._color = QColor(0, 0, 0, 0)
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)
        try:
            painter.drawTiledPixmap(self.frameRect(), self._background)
            painter.fillRect(self.frameRect(), self._color)
        finally:
            painter.end()
        super().paintEvent(event)

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()


class ColorPicker(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._preview = ColorPickerPreview(self)
        self._preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._button = QPushButton("Change", self)
        self._button.clicked.connect(self._on_button_click)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._preview)
        layout.addWidget(self._button)
        self._preview.setMinimumHeight(self._button.height())
        self._color = QColor(0, 0, 0, 0)

    def _on_button_click(self, event: QMouseEvent) -> None:
        color = QColorDialog.getColor(self._color, self)
        if color.isValid():
            self.set_color(color)

    def get_color(self) -> QColor:
        return self._color

    def set_color(self, color: QColor) -> None:
        if self._color != color:
            self._preview.set_color(color)
            self._color = color
            self.changed.emit()

    color = pyqtProperty(QColor, get_color, set_color, user=True)


class Dialog(QDialog):
    """A dialog that automatically closes and disconnects all signals after
    exiting.
    """

    def __init__(self, main_window: QMainWindow) -> None:
        super().__init__(main_window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

    def done(self, code: int) -> None:
        ret = super().done(code)
        self.close()
        return ret


async def load_dialog(
    parent: QWidget,
    file_filter: str,
    directory: Optional[Path] = None,
) -> Optional[Path]:
    real_directory = (
        str(directory) if directory is not None else cast(str, QDir.homePath())
    )
    dialog = QFileDialog(
        parent, "Open File", directory=real_directory, filter=file_filter
    )
    dialog.setFileMode(dialog.ExistingFile)
    dialog.setAcceptMode(dialog.AcceptOpen)
    if await async_dialog_exec(dialog):
        return Path(dialog.selectedFiles()[0])
    return None


async def save_dialog(
    parent: QWidget,
    file_filter: Optional[str],
    directory: Optional[Path] = None,
    file_name: Optional[str] = None,
) -> Optional[Path]:
    real_directory = (
        str(directory) if directory is not None else cast(str, QDir.homePath())
    )
    if file_name:
        real_directory += "/" + file_name

    dialog = QFileDialog(
        parent,
        "Save File",
        directory=real_directory,
        filter=file_filter or "Any File (*)",
    )
    dialog.setFileMode(dialog.AnyFile)
    dialog.setAcceptMode(dialog.AcceptSave)
    if await async_dialog_exec(dialog):
        return Path(dialog.selectedFiles()[0])
    return None


async def time_jump_dialog(
    parent: QWidget,
    value: int = 0,
    relative_label: str = "Time:",
    absolute_label: str = "Time:",
    relative_checked: bool = True,
    show_radio: bool = True,
) -> Optional[tuple[int, bool]]:
    class TimeJumpDialog(QDialog):
        def __init__(self, parent: QWidget) -> None:
            super().__init__(parent)
            self.setWindowTitle("Select time...")

            self._label = QLabel("", self)
            self._time_edit = TimeEdit(self)
            self._radio_rel = QRadioButton("Relative", self)
            self._radio_abs = QRadioButton("Absolute", self)
            if relative_checked:
                self._radio_rel.setChecked(True)
            else:
                self._radio_abs.setChecked(True)
            strip = QDialogButtonBox(self)
            strip.addButton(strip.Ok)
            strip.addButton(strip.Cancel)

            if not show_radio:
                self._radio_abs.setHidden(True)
                self._radio_rel.setHidden(True)

            strip.accepted.connect(self.accept)
            strip.rejected.connect(self.reject)
            self._radio_rel.clicked.connect(self._on_radio_click)
            self._radio_abs.clicked.connect(self._on_radio_click)

            layout = QVBoxLayout(self)
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

        def value(self) -> tuple[int, bool]:
            return (self._time_edit.get_value(), self._radio_rel.isChecked())

    dialog = TimeJumpDialog(parent)
    if await async_dialog_exec(dialog):
        return dialog.value()
    return None


def get_text_edit_row_height(editor: QPlainTextEdit, rows: int) -> int:
    metrics = QFontMetrics(editor.document().defaultFont())
    margins = editor.contentsMargins()
    return int(
        metrics.lineSpacing() * rows
        + (editor.document().documentMargin() + editor.frameWidth()) * 2
        + margins.top()
        + margins.bottom()
        + 1
    )


class ImmediateDataWidgetMapper(QObject):
    def __init__(
        self,
        model: QAbstractItemModel,
        signal_map: Optional[dict[type[QWidget], str]] = None,
    ) -> None:
        super().__init__()
        self._model = model
        self._mappings: list[tuple[QWidget, int]] = []
        self._row_idx: Optional[int] = None
        self._item_delegate = QItemDelegate(self)
        self._ignoring = 0

        self._signal_map: dict[type[QWidget], str] = {
            QCheckBox: "clicked",
            QSpinBox: "valueChanged",
            QDoubleSpinBox: "valueChanged",
            QComboBox: "currentTextChanged",
            ColorPicker: "changed",
            TimeEdit: "value_changed",
        }
        if signal_map:
            self._signal_map.update(signal_map)

        model.dataChanged.connect(self._model_data_change)

    def add_mapping(self, widget: QWidget, idx: int) -> None:
        for type_, signal_name in self._signal_map.items():
            if isinstance(widget, type_):
                signal = getattr(widget, signal_name)
                signal.connect(partial(self._widget_data_change, idx))
                self._mappings.append((widget, idx))
                return
        raise RuntimeError(f'unknown widget type: "{type(widget)}"')

    def set_current_index(self, row_idx: Optional[int]) -> None:
        self._row_idx = row_idx
        for widget, col_idx in self._mappings:
            self._write_to_widget(widget, row_idx, col_idx)

    def _widget_data_change(self, sender_col_idx: int) -> None:
        if self._row_idx is None:
            return
        for widget, col_idx in self._mappings:
            if sender_col_idx == col_idx:
                with self._ignore_signals():
                    self._write_to_model(widget, self._row_idx, col_idx)

    def _model_data_change(
        self, top_left: QModelIndex, bottom_right: QModelIndex
    ) -> None:
        if self._row_idx is None or self._ignoring:
            return
        for widget, col_idx in self._mappings:
            if (
                top_left.row() <= self._row_idx <= bottom_right.row()
                and top_left.column() <= col_idx <= bottom_right.column()
            ):
                self._write_to_widget(widget, self._row_idx, col_idx)

    def _write_to_widget(
        self, widget: QWidget, row_idx: Optional[int], col_idx: int
    ) -> None:
        if self._ignoring:
            return
        name = widget.metaObject().userProperty().name()
        cur_value = (
            QVariant()
            if row_idx is None
            else self._model.index(row_idx, col_idx).data(
                Qt.ItemDataRole.EditRole
            )
        )
        prev_value = widget.property(name)
        if cur_value != prev_value:
            if isinstance(widget, QComboBox) and row_idx is not None:
                widget.blockSignals(True)
                cb_row_idx = widget.findText(cur_value)
                widget.setCurrentIndex(cb_row_idx)
                widget.blockSignals(False)
            widget.setProperty(name, cur_value)

    def _write_to_model(
        self, widget: QWidget, row_idx: int, col_idx: int
    ) -> None:
        name = widget.metaObject().userProperty().name()
        cur_value = widget.property(name)
        prev_value = self._model.data(
            self._model.index(row_idx, col_idx), Qt.ItemDataRole.EditRole
        )
        if cur_value != prev_value:
            self._model.setData(
                self._model.index(row_idx, col_idx),
                cur_value,
                Qt.ItemDataRole.EditRole,
            )

    @contextlib.contextmanager
    def _ignore_signals(self) -> Any:
        self._ignoring += 1
        try:
            yield
        finally:
            self._ignoring -= 1


def build_splitter(
    parent: QWidget,
    widgets: list[tuple[int, QWidget]],
    orientation: Qt.Orientation,
) -> QSplitter:
    splitter = QSplitter(parent)
    splitter.setOrientation(orientation)
    for i, item in enumerate(widgets):
        stretch_factor, widget = item
        splitter.addWidget(widget)
        splitter.setStretchFactor(i, stretch_factor)
    return splitter
