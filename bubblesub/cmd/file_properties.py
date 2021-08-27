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

from collections import OrderedDict
from typing import cast

import ass_tag_parser
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.errors import ResourceUnavailable
from bubblesub.ui.util import (
    Dialog,
    async_dialog_exec,
    async_slot,
    show_prompt,
)


def _rescale_styles(api: Api, factor: float) -> None:
    for style in api.subs.styles:
        style.scale(factor)


def _rescale_ass_tags(api: Api, x_factor: float, y_factor: float) -> None:
    for event in api.subs.events:
        try:
            ass_line = ass_tag_parser.parse_ass(event.text)
        except ass_tag_parser.ParseError:
            return

        for item in ass_line:
            if isinstance(
                item,
                (
                    ass_tag_parser.AssTagBorder,
                    ass_tag_parser.AssTagXBorder,
                    ass_tag_parser.AssTagYBorder,
                    ass_tag_parser.AssTagShadow,
                    ass_tag_parser.AssTagXShadow,
                    ass_tag_parser.AssTagYShadow,
                ),
            ):
                item.size *= y_factor

            elif isinstance(
                item,
                (
                    ass_tag_parser.AssTagPosition,
                    ass_tag_parser.AssTagRotationOrigin,
                ),
            ):
                item.x = int(item.x * x_factor)
                item.y = int(item.y * y_factor)

            elif isinstance(item, ass_tag_parser.AssTagMove):
                item.x1 = int(item.x1 * x_factor)
                item.y1 = int(item.y1 * y_factor)
                item.x2 = int(item.x2 * x_factor)
                item.y2 = int(item.y2 * y_factor)

            elif isinstance(item, ass_tag_parser.AssTagFontSize):
                item.size = int(item.size * y_factor)

        event.text = ass_tag_parser.compose_ass(ass_line)


class _OptionsGropuBox(QGroupBox):
    def __init__(self, api: Api, parent: QWidget) -> None:
        super().__init__("Options:", parent)
        self._api = api

        self.res_x_edit = QSpinBox(self)
        self.res_x_edit.setMinimum(0)
        self.res_x_edit.setMaximum(99999)
        self.res_y_edit = QSpinBox(self)
        self.res_y_edit.setMinimum(0)
        self.res_y_edit.setMaximum(99999)

        get_resolution_button = QPushButton("Take from video", self)
        get_resolution_button.clicked.connect(
            self._on_get_resolution_button_click
        )

        self.ycbcr_matrix_combo_box = QComboBox(self)
        for value in [
            "TV.601",
            "PC.601",
            "TV.709",
            "PC.709",
            "TV.FCC",
            "PC.FCC",
            "TV.240M",
            "PC.240M",
        ]:
            self.ycbcr_matrix_combo_box.addItem(value, userData=value)

        self.wrap_mode_combo_box = QComboBox(self)
        for key, value in {
            "0": "Smart wrapping, top line is wider",
            "1": "End-of-line word wrapping, only \\N breaks",
            "2": "No word wrapping, both \\n and \\N break",
            "3": "Smart wrapping, bottom line is wider",
        }.items():
            self.wrap_mode_combo_box.addItem(value, userData=key)

        self.scale_check_box = QCheckBox("Scale borders and shadows", self)

        layout = QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)

        layout.addWidget(QLabel("Resolution:", self), 0, 0)
        sublayout = QHBoxLayout()
        sublayout.addWidget(self.res_x_edit)
        sublayout.addWidget(self.res_y_edit)
        sublayout.addWidget(get_resolution_button)
        layout.addLayout(sublayout, 0, 1)

        layout.addWidget(QLabel("YCbCr matrix:", self), 1, 0)
        layout.addWidget(self.ycbcr_matrix_combo_box, 1, 1)

        layout.addWidget(QLabel("Wrap style:", self), 2, 0)
        layout.addWidget(self.wrap_mode_combo_box, 2, 1)

        layout.addWidget(self.scale_check_box, 3, 1)

    def _on_get_resolution_button_click(self) -> None:
        try:
            self.res_x_edit.setValue(self._api.video.current_stream.width)
            self.res_y_edit.setValue(self._api.video.current_stream.height)
        except ResourceUnavailable:
            self.res_x_edit.setValue(0)
            self.res_y_edit.setValue(0)


class _MetadataGroupBox(QGroupBox):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Meta data:", parent)
        self.model = QStandardItemModel(self)
        self.model.setHorizontalHeaderLabels(["Key", "Value"])

        self._table_view = QTableView(self)
        self._table_view.setModel(self.model)
        self._table_view.setTabKeyNavigation(False)

        self._table_view.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self._table_view.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )

        self._table_view.verticalHeader().setSectionsMovable(True)
        self._table_view.verticalHeader().setDragEnabled(True)
        self._table_view.verticalHeader().setDragDropMode(
            QAbstractItemView.InternalMove
        )

        self._table_view.verticalHeader().setDefaultSectionSize(
            int(self._table_view.fontMetrics().height() * 1.8)
        )

        strip = QWidget(self)
        add_row_button = QPushButton("Add new row", strip)
        del_rows_button = QPushButton("Remove selected rows", strip)
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(0, 0, 0, 0)
        strip_layout.addWidget(add_row_button)
        strip_layout.addWidget(del_rows_button)
        strip_layout.addStretch()

        add_row_button.clicked.connect(self._on_add_button_click)
        del_rows_button.clicked.connect(self._on_delete_rows_button_click)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table_view)
        layout.addWidget(strip)

    def get_data(self) -> dict[str, str]:
        metadata: dict[str, str] = OrderedDict()
        for y in range(self.model.rowCount()):
            visual_y = self._table_view.verticalHeader().visualIndex(y)
            key = self.model.item(visual_y, 0).text().strip()
            value = self.model.item(visual_y, 1).text().strip()
            if key and value:
                metadata[key] = value
        return metadata

    def _on_add_button_click(self) -> None:
        self.model.appendRow([QStandardItem(""), QStandardItem("")])

    def _on_delete_rows_button_click(self) -> None:
        rows = set(
            index.row()
            for index in self._table_view.selectionModel().selectedIndexes()
        )
        for row in sorted(rows, reverse=True):
            self.model.removeRow(row)


class _FilePropertiesDialog(Dialog):
    def __init__(self, api: Api, main_window: QMainWindow) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._api = api

        self._metadata_group_box = _MetadataGroupBox(self)

        strip = QDialogButtonBox(self)
        strip.setOrientation(Qt.Orientation.Horizontal)
        strip.addButton("OK", strip.AcceptRole)
        apply_button = strip.addButton("Apply", strip.ApplyRole)
        apply_button.clicked.connect(self._commit)
        strip.addButton("Cancel", strip.RejectRole)
        strip.accepted.connect(self.accept)
        strip.rejected.connect(self.reject)

        self._options_group_box = _OptionsGropuBox(api, self)

        layout = QVBoxLayout(self)
        layout.addWidget(self._options_group_box)
        layout.addWidget(self._metadata_group_box)
        layout.addWidget(strip)

        self.accepted.connect(self._commit)

        self._load()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle("File properties")
        self.resize(600, 600)

    def _load(self) -> None:
        self._options_group_box.res_x_edit.setValue(
            int(cast(str, self._api.subs.script_info.get("PlayResX", "0")))
        )
        self._options_group_box.res_y_edit.setValue(
            int(cast(str, self._api.subs.script_info.get("PlayResY", "0")))
        )

        self._options_group_box.ycbcr_matrix_combo_box.setCurrentIndex(
            self._options_group_box.ycbcr_matrix_combo_box.findData(
                self._api.subs.script_info.get("YCbCr Matrix")
            )
        )

        self._options_group_box.wrap_mode_combo_box.setCurrentIndex(
            self._options_group_box.wrap_mode_combo_box.findData(
                self._api.subs.script_info.get("WrapStyle")
            )
        )

        self._options_group_box.scale_check_box.setChecked(
            self._api.subs.script_info.get("ScaledBorderAndShadow", "yes")
            == "yes"
        )

        for key, value in self._api.subs.script_info.items():
            if key not in [
                "PlayResX",
                "PlayResY",
                "YCbCr Matrix",
                "WrapStyle",
                "ScaledBorderAndShadow",
                "ScriptType",
            ]:
                self._metadata_group_box.model.appendRow(
                    [QStandardItem(key), QStandardItem(value)]
                )

    @async_slot()
    async def _commit(self) -> None:
        old_res = (
            int(cast(str, self._api.subs.script_info.get("PlayResX", "0"))),
            int(cast(str, self._api.subs.script_info.get("PlayResY", "0"))),
        )

        self._api.subs.script_info.clear()

        play_res_x = str(self._options_group_box.res_x_edit.value())
        play_res_y = str(self._options_group_box.res_y_edit.value())
        ycbcr = self._options_group_box.ycbcr_matrix_combo_box.currentData()
        wrap_style = self._options_group_box.wrap_mode_combo_box.currentData()
        border_and_shadow = self._options_group_box.scale_check_box.isChecked()

        self._api.subs.script_info.update(
            {
                "ScriptType": "v4.00+",
                "PlayResX": play_res_x,
                "PlayResY": play_res_y,
                "YCbCr Matrix": ycbcr,
                "WrapStyle": wrap_style,
                "ScaledBorderAndShadow": ["no", "yes"][border_and_shadow],
            }
        )

        self._api.subs.script_info.update(self._metadata_group_box.get_data())

        new_res = (
            int(cast(str, self._api.subs.script_info.get("PlayResX", "0"))),
            int(cast(str, self._api.subs.script_info.get("PlayResY", "0"))),
        )
        if (
            old_res != new_res
            and all(old_res)
            and all(new_res)
            and await show_prompt(
                "The resolution was changed. "
                "Do you want to rescale all the styles now?",
                self,
            )
        ):
            x_factor = new_res[0] / old_res[0]
            y_factor = new_res[1] / old_res[1]
            _rescale_styles(self._api, y_factor)
            _rescale_ass_tags(self._api, x_factor, y_factor)


class FilePropertiesCommand(BaseCommand):
    names = ["file-properties"]
    help_text = "Opens up the metadata editor dialog."

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QMainWindow) -> None:
        with self.api.undo.capture():
            dialog = _FilePropertiesDialog(self.api, main_window)
            await async_dialog_exec(dialog)


COMMANDS = [FilePropertiesCommand]
