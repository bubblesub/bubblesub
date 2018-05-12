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

"""Styles manager command."""

import re
import typing as T
from copy import copy

import PIL.Image
import PIL.ImageQt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ass.file
import bubblesub.ass.style
import bubblesub.ass.writer
import bubblesub.data
import bubblesub.ui.ass_renderer
import bubblesub.ui.util
from bubblesub.api.cmd import BaseCommand
from bubblesub.ui.model.styles import StylesModel, StylesModelColumn


class _StylePreview(QtWidgets.QGroupBox):
    def __init__(
            self,
            api: bubblesub.api.Api,
            selection_model: QtCore.QItemSelectionModel,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__('Preview', parent)
        self._api = api
        self._selection_model = selection_model

        self._ctx = bubblesub.ui.ass_renderer.AssContext()
        self._renderer = self._ctx.make_renderer()
        self._renderer.set_fonts()

        self._editor = QtWidgets.QPlainTextEdit()
        self._editor.setPlainText(api.opt.general.styles.preview_test_text)
        self._editor.setFixedWidth(400)
        self._editor.setTabChangesFocus(True)
        self._editor.setFixedHeight(
            bubblesub.ui.util.get_text_edit_row_height(self._editor, 2)
        )

        self._background_combobox = QtWidgets.QComboBox()
        for i, path in enumerate(
                bubblesub.data.get_all(api.opt, 'style_preview_bk')
        ):
            self._background_combobox.addItem(path.name, path.resolve())
            if path.name == api.opt.general.styles.preview_background:
                self._background_combobox.setCurrentIndex(i)

        self._preview_box = QtWidgets.QLabel(self)
        self._preview_box.setLineWidth(1)
        self._preview_box.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._preview_box.setFrameShadow(QtWidgets.QFrame.Sunken)
        self._preview_box.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Ignored
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._editor)
        layout.addWidget(self._background_combobox)
        layout.addWidget(self._preview_box)

        self.update_preview()
        self._editor.textChanged.connect(self._on_text_change)
        self._background_combobox.currentIndexChanged.connect(
            self._on_background_change
        )
        api.subs.styles.item_changed.connect(self.update_preview)
        api.subs.styles.items_inserted.connect(self.update_preview)
        api.subs.styles.items_removed.connect(self.update_preview)
        selection_model.selectionChanged.connect(self.update_preview)

    def _on_background_change(self) -> None:
        self.update_preview()
        self._api.opt.general.styles.preview_background = (
            self._background_combobox.currentData().name
        )

    def _on_text_change(self) -> None:
        self.update_preview()
        self._api.opt.general.styles.preview_test_text = (
            self._editor.toPlainText()
        )

    @property
    def _selected_style(self) -> T.Optional[bubblesub.ass.style.Style]:
        try:
            idx = self._selection_model.selectedIndexes()[0].row()
        except IndexError:
            return None
        else:
            return self._api.subs.styles[idx]

    def update_preview(self) -> None:
        selected_style = self._selected_style
        if not selected_style:
            self._preview_box.clear()
            return

        resolution = (self._preview_box.width(), self._preview_box.height())
        if resolution[0] <= 0 or resolution[1] <= 0:
            self._preview_box.clear()
            return

        fake_style = copy(selected_style)
        fake_style.name = 'Default'
        if self._api.media.is_loaded:
            fake_style.scale(resolution[1] / self._api.media.video.height)

        fake_style_list = bubblesub.ass.style.StyleList()
        fake_style_list.insert(0, [fake_style])

        fake_event_list = bubblesub.ass.event.EventList()
        fake_event_list.insert_one(
            0,
            start=0,
            end=1000,
            text=self._editor.toPlainText().replace('\n', '\\N'),
            style=fake_style.name
        )

        track = self._ctx.make_track()
        track.populate(fake_style_list, fake_event_list, play_res=resolution)

        self._renderer.set_all_sizes(resolution)
        imgs = self._renderer.render_frame(track, now=0)

        image = PIL.Image.new(mode='RGBA', size=resolution)

        background_path = self._background_combobox.currentData()
        if background_path and background_path.exists():
            background = PIL.Image.open(background_path)
            for y in range(0, resolution[1], background.height):
                for x in range(0, resolution[0], background.width):
                    image.paste(background, (x, y))

        for img in imgs:
            red, green, blue, alpha = img.rgba
            color = PIL.Image.new(
                'RGBA', image.size, (red, green, blue, 255 - alpha)
            )

            mask = PIL.Image.new('L', image.size, (255,))
            mask_data = mask.load()
            for y in range(img.h):
                for x in range(img.w):
                    mask_data[img.dst_x + x, img.dst_y + y] = 255 - img[x, y]

            image = PIL.Image.composite(image, color, mask)

        image = PIL.ImageQt.ImageQt(image)
        image = QtGui.QImage(image)
        self._preview_box.setPixmap(QtGui.QPixmap.fromImage(image))


class _StyleList(QtWidgets.QWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            model: StylesModel,
            selection_model: QtCore.QItemSelectionModel,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self._api = api
        selection_model.selectionChanged.connect(self._on_selection_change)

        self._styles_list_view = QtWidgets.QListView(self)
        self._styles_list_view.setModel(model)
        self._styles_list_view.setSelectionModel(selection_model)

        self._add_button = QtWidgets.QPushButton('Add', self)
        self._add_button.clicked.connect(self._on_add_button_click)
        self._remove_button = QtWidgets.QPushButton('Remove', self)
        self._remove_button.setEnabled(False)
        self._remove_button.clicked.connect(self._on_remove_button_click)
        self._duplicate_button = QtWidgets.QPushButton('Duplicate', self)
        self._duplicate_button.setEnabled(False)
        self._duplicate_button.clicked.connect(self._on_duplicate_button_click)
        self._move_up_button = QtWidgets.QPushButton('Move up', self)
        self._move_up_button.setEnabled(False)
        self._move_up_button.clicked.connect(self._on_move_up_button_click)
        self._move_down_button = QtWidgets.QPushButton('Move down', self)
        self._move_down_button.setEnabled(False)
        self._move_down_button.clicked.connect(self._on_move_down_button_click)
        self._rename_button = QtWidgets.QPushButton('Rename', self)
        self._rename_button.setEnabled(False)
        self._rename_button.clicked.connect(self._on_rename_button_click)

        strip = QtWidgets.QWidget(self)
        strip_layout = QtWidgets.QGridLayout(strip)
        strip_layout.setContentsMargins(0, 0, 0, 0)
        strip_layout.addWidget(self._add_button, 0, 0)
        strip_layout.addWidget(self._remove_button, 0, 1)
        strip_layout.addWidget(self._duplicate_button, 0, 2)
        strip_layout.addWidget(self._move_up_button, 1, 0)
        strip_layout.addWidget(self._move_down_button, 1, 1)
        strip_layout.addWidget(self._rename_button, 1, 2)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._styles_list_view)
        layout.addWidget(strip)

    @property
    def _selected_style(self) -> T.Optional[bubblesub.ass.style.Style]:
        selected_row = self._selected_row
        if selected_row is None:
            return None
        return self._api.subs.styles[selected_row]

    @property
    def _selected_row(self) -> T.Optional[int]:
        indexes = self._styles_list_view.selectedIndexes()
        if not indexes:
            return None
        return T.cast(int, indexes[0].row())

    def _on_selection_change(
            self,
            selected: QtCore.QItemSelection,
            _deselected: QtCore.QItemSelection
    ) -> None:
        anything_selected = len(selected.indexes()) > 0
        self._remove_button.setEnabled(anything_selected)
        self._rename_button.setEnabled(anything_selected)
        self._duplicate_button.setEnabled(anything_selected)
        self._move_up_button.setEnabled(
            anything_selected
            and selected.indexes()[0].row() > 0
        )
        self._move_down_button.setEnabled(
            anything_selected
            and selected.indexes()[0].row() < len(self._api.subs.styles) - 1
        )

    def _on_add_button_click(self, _event: QtGui.QMouseEvent) -> None:
        style_name = self._prompt_for_unique_style_name()
        if not style_name:
            return

        style = self._api.subs.styles.insert_one(style_name)
        idx = self._api.subs.styles.index(style)
        assert idx is not None

        self._styles_list_view.selectionModel().select(
            self._styles_list_view.model().index(idx, 0),
            QtCore.QItemSelectionModel.Clear |
            QtCore.QItemSelectionModel.Select
        )

    def _prompt_for_unique_style_name(
            self,
            style_name: str = ''
    ) -> T.Optional[str]:
        prompt_text = 'Name of the new style:'
        while True:
            dialog = QtWidgets.QInputDialog(self)
            dialog.setLabelText(prompt_text)
            dialog.setTextValue(style_name)
            dialog.setInputMode(QtWidgets.QInputDialog.TextInput)
            if not dialog.exec_():
                return None
            style_name = dialog.textValue()

            exists = False
            for style in self._api.subs.styles:
                if style.name == style_name:
                    exists = True

            if not exists:
                return style_name

            prompt_text = (
                '"{}" already exists. Choose different name:'
                .format(style_name)
            )

    def _on_remove_button_click(self, _event: QtGui.QMouseEvent) -> None:
        style = self._selected_style
        assert style is not None

        if not bubblesub.ui.util.ask(
                f'Are you sure you want to remove style "{style.name}"?'
        ):
            return

        idx = self._api.subs.styles.index(style)
        assert idx is not None

        self._styles_list_view.selectionModel().clear()
        with self._api.undo.capture():
            self._api.subs.styles.remove(idx, 1)

    def _on_duplicate_button_click(self, _event: QtGui.QMouseEvent) -> None:
        style = self._selected_style
        assert style is not None

        idx = self._api.subs.styles.index(style)
        assert idx is not None

        style_copy = copy(style)
        style_copy.name += ' (copy)'
        with self._api.undo.capture():
            self._api.subs.styles.insert(idx + 1, [style_copy])
        self._styles_list_view.selectionModel().select(
            self._styles_list_view.model().index(idx + 1, 0),
            QtCore.QItemSelectionModel.Clear |
            QtCore.QItemSelectionModel.Select
        )

    def _on_move_up_button_click(self, _event: QtGui.QMouseEvent) -> None:
        style = self._selected_style
        assert style is not None

        idx = self._api.subs.styles.index(style)
        assert idx is not None

        with self._api.undo.capture():
            self._api.subs.styles.move(idx, idx - 1)
        self._styles_list_view.selectionModel().select(
            self._styles_list_view.model().index(idx - 1, 0),
            QtCore.QItemSelectionModel.Clear |
            QtCore.QItemSelectionModel.Select
        )

    def _on_move_down_button_click(self, _event: QtGui.QMouseEvent) -> None:
        style = self._selected_style
        assert style is not None

        idx = self._api.subs.styles.index(style)
        assert idx is not None

        with self._api.undo.capture():
            self._api.subs.styles.move(idx, idx + 1)
        self._styles_list_view.selectionModel().select(
            self._styles_list_view.model().index(idx + 1, 0),
            QtCore.QItemSelectionModel.Clear |
            QtCore.QItemSelectionModel.Select
        )

    def _on_rename_button_click(self, _event: QtGui.QMouseEvent) -> None:
        style = self._selected_style
        assert style is not None

        idx = self._api.subs.styles.index(style)
        assert idx is not None

        old_name = style.name
        new_name = self._prompt_for_unique_style_name(old_name)
        if not new_name:
            return

        with self._api.undo.capture():
            style.name = new_name
            for line in self._api.subs.events:
                if line.style == old_name:
                    line.style = new_name

        self._styles_list_view.selectionModel().select(
            self._styles_list_view.model().index(idx, 0),
            QtCore.QItemSelectionModel.Select
        )


class _FontGroupBox(QtWidgets.QGroupBox):
    def __init__(
            self,
            parent: QtWidgets.QWidget,
            mapper: QtWidgets.QDataWidgetMapper
    ) -> None:
        super().__init__('Font', parent)
        self.font_name_edit = QtWidgets.QComboBox(self)
        self.font_name_edit.setEditable(False)
        self.font_name_edit.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum
        )
        self.font_name_edit.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.font_size_edit = QtWidgets.QSpinBox(self)
        self.font_size_edit.setMinimum(0)
        self.bold_checkbox = QtWidgets.QCheckBox('Bold', self)
        self.italic_checkbox = QtWidgets.QCheckBox('Italic', self)
        self.underline_checkbox = QtWidgets.QCheckBox('Underline', self)
        self.strike_out_checkbox = QtWidgets.QCheckBox('Strike-out', self)

        all_fonts = sorted(set(
            re.sub(r' \[.*\]', '', font_name)
            for font_name in QtGui.QFontDatabase().families()
        ))
        self.font_name_edit.addItems(all_fonts)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(QtWidgets.QLabel('Name:', self), 0, 0)
        layout.addWidget(self.font_name_edit, 0, 1, 1, 2)
        layout.addWidget(QtWidgets.QLabel('Size:', self), 1, 0)
        layout.addWidget(self.font_size_edit, 1, 1, 1, 2)
        layout.addWidget(QtWidgets.QLabel('Style:', self), 2, 0)
        layout.addWidget(self.bold_checkbox, 2, 1)
        layout.addWidget(self.italic_checkbox, 3, 1)
        layout.addWidget(self.underline_checkbox, 2, 2)
        layout.addWidget(self.strike_out_checkbox, 3, 2)

        mapper.addMapping(self.font_name_edit, StylesModelColumn.FontName)
        mapper.addMapping(self.font_size_edit, StylesModelColumn.FontSize)
        mapper.addMapping(self.bold_checkbox, StylesModelColumn.Bold)
        mapper.addMapping(self.italic_checkbox, StylesModelColumn.Italic)
        mapper.addMapping(self.underline_checkbox, StylesModelColumn.Underline)
        mapper.addMapping(
            self.strike_out_checkbox, StylesModelColumn.StrikeOut
        )


class _AlignmentGroupBox(QtWidgets.QGroupBox):
    changed = QtCore.pyqtSignal()

    def __init__(
            self,
            parent: QtWidgets.QWidget,
            mapper: QtWidgets.QDataWidgetMapper
    ) -> None:
        super().__init__('Alignment', parent)
        self.radio_buttons = {
            x: QtWidgets.QRadioButton(
                [
                    '\N{SOUTH WEST ARROW}',
                    '\N{DOWNWARDS ARROW}',
                    '\N{SOUTH EAST ARROW}',
                    '\N{LEFTWARDS ARROW}',
                    '\N{BLACK DIAMOND}',
                    '\N{RIGHTWARDS ARROW}',
                    '\N{NORTH WEST ARROW}',
                    '\N{UPWARDS ARROW}',
                    '\N{NORTH EAST ARROW}',
                ][x - 1],
                self
            )
            for x in range(1, 10)
        }
        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.addWidget(self.radio_buttons[7], 0, 0)
        layout.addWidget(self.radio_buttons[8], 0, 1)
        layout.addWidget(self.radio_buttons[9], 0, 2)
        layout.addWidget(self.radio_buttons[4], 1, 0)
        layout.addWidget(self.radio_buttons[5], 1, 1)
        layout.addWidget(self.radio_buttons[6], 1, 2)
        layout.addWidget(self.radio_buttons[1], 2, 0)
        layout.addWidget(self.radio_buttons[2], 2, 1)
        layout.addWidget(self.radio_buttons[3], 2, 2)

        for radio_button in self.radio_buttons.values():
            radio_button.toggled.connect(
                lambda _event: self.changed.emit()
            )

        mapper.addMapping(self, StylesModelColumn.Alignment)

    def get_value(self) -> int:
        for idx, radio_button in self.radio_buttons.items():
            if radio_button.isChecked():
                return idx
        return -1

    def set_value(self, value: int) -> None:
        if value in self.radio_buttons:
            self.radio_buttons[value].setChecked(True)

    value = QtCore.pyqtProperty(int, get_value, set_value, user=True)


class _ColorsGroupBox(QtWidgets.QGroupBox):
    def __init__(
            self,
            parent: QtWidgets.QWidget,
            mapper: QtWidgets.QDataWidgetMapper
    ) -> None:
        super().__init__('Colors', parent)
        self.primary_color_button = bubblesub.ui.util.ColorPicker(self)
        self.secondary_color_button = bubblesub.ui.util.ColorPicker(self)
        self.outline_color_button = bubblesub.ui.util.ColorPicker(self)
        self.back_color_button = bubblesub.ui.util.ColorPicker(self)

        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.addWidget(QtWidgets.QLabel('Primary:', self), 0, 0)
        layout.addWidget(self.primary_color_button, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Secondary:', self), 1, 0)
        layout.addWidget(self.secondary_color_button, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Outline:', self), 2, 0)
        layout.addWidget(self.outline_color_button, 2, 1)
        layout.addWidget(QtWidgets.QLabel('Shadow:', self), 3, 0)
        layout.addWidget(self.back_color_button, 3, 1)

        mapper.addMapping(
            self.primary_color_button, StylesModelColumn.PrimaryColor
        )
        mapper.addMapping(
            self.secondary_color_button, StylesModelColumn.SecondaryColor
        )
        mapper.addMapping(
            self.back_color_button, StylesModelColumn.BackColor
        )
        mapper.addMapping(
            self.outline_color_button, StylesModelColumn.OutlineColor
        )


class _OutlineGroupBox(QtWidgets.QGroupBox):
    def __init__(
            self,
            parent: QtWidgets.QWidget,
            mapper: QtWidgets.QDataWidgetMapper
    ) -> None:
        super().__init__('Outline', parent)
        self.outline_width_edit = QtWidgets.QDoubleSpinBox(self)
        self.outline_width_edit.setMinimum(0)
        self.outline_width_edit.setMaximum(999)
        self.shadow_width_edit = QtWidgets.QDoubleSpinBox(self)
        self.shadow_width_edit.setMinimum(0)
        self.shadow_width_edit.setMaximum(999)

        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.addWidget(QtWidgets.QLabel('Outline:', self), 0, 0)
        layout.addWidget(self.outline_width_edit, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Shadow:', self), 1, 0)
        layout.addWidget(self.shadow_width_edit, 1, 1)

        mapper.addMapping(
            self.shadow_width_edit, StylesModelColumn.ShadowWidth
        )
        mapper.addMapping(
            self.outline_width_edit, StylesModelColumn.OutlineWidth
        )


class _MarginGroupBox(QtWidgets.QGroupBox):
    def __init__(
            self,
            parent: QtWidgets.QWidget,
            mapper: QtWidgets.QDataWidgetMapper
    ) -> None:
        super().__init__('Margins', parent)
        self.margin_left_edit = QtWidgets.QSpinBox(self)
        self.margin_left_edit.setMinimum(0)
        self.margin_left_edit.setMaximum(999)
        self.margin_right_edit = QtWidgets.QSpinBox(self)
        self.margin_right_edit.setMinimum(0)
        self.margin_right_edit.setMaximum(999)
        self.margin_vertical_edit = QtWidgets.QSpinBox(self)
        self.margin_vertical_edit.setMinimum(0)
        self.margin_vertical_edit.setMaximum(999)

        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.addWidget(QtWidgets.QLabel('Left:', self), 0, 0)
        layout.addWidget(self.margin_left_edit, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Right:', self), 1, 0)
        layout.addWidget(self.margin_right_edit, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Vertical:', self), 2, 0)
        layout.addWidget(self.margin_vertical_edit, 2, 1)

        mapper.addMapping(
            self.margin_left_edit, StylesModelColumn.MarginLeft
        )
        mapper.addMapping(
            self.margin_right_edit, StylesModelColumn.MarginRight
        )
        mapper.addMapping(
            self.margin_vertical_edit, StylesModelColumn.MarginVertical
        )


class _MiscGroupBox(QtWidgets.QGroupBox):
    def __init__(
            self,
            parent: QtWidgets.QWidget,
            mapper: QtWidgets.QDataWidgetMapper
    ) -> None:
        super().__init__('Transformations', parent)
        self.scale_x_edit = QtWidgets.QDoubleSpinBox(self)
        self.scale_x_edit.setMinimum(0)
        self.scale_x_edit.setMaximum(999)
        self.scale_y_edit = QtWidgets.QDoubleSpinBox(self)
        self.scale_y_edit.setMinimum(0)
        self.scale_y_edit.setMaximum(999)
        self.angle_edit = QtWidgets.QDoubleSpinBox(self)
        self.angle_edit.setMinimum(0)
        self.angle_edit.setMaximum(999)
        self.spacing_edit = QtWidgets.QDoubleSpinBox(self)
        self.spacing_edit.setMinimum(0)
        self.spacing_edit.setMaximum(999)

        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.addWidget(QtWidgets.QLabel('Scale X:', self), 0, 0)
        layout.addWidget(self.scale_x_edit, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Scale Y:', self), 1, 0)
        layout.addWidget(self.scale_y_edit, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Angle:', self), 2, 0)
        layout.addWidget(self.angle_edit, 2, 1)
        layout.addWidget(QtWidgets.QLabel('Spacing:', self), 3, 0)
        layout.addWidget(self.spacing_edit, 3, 1)

        mapper.addMapping(self.scale_x_edit, StylesModelColumn.ScaleX)
        mapper.addMapping(self.scale_y_edit, StylesModelColumn.ScaleY)
        mapper.addMapping(self.angle_edit, StylesModelColumn.Angle)
        mapper.addMapping(self.spacing_edit, StylesModelColumn.Spacing)


class _StyleEditor(QtWidgets.QWidget):
    def __init__(
            self,
            model: StylesModel,
            selection_model: QtCore.QItemSelectionModel,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self._mapper = QtWidgets.QDataWidgetMapper()
        self._mapper.setModel(model)
        self._model = model
        selection_model.selectionChanged.connect(self._on_selection_change)

        self.font_group_box = _FontGroupBox(self, self._mapper)
        self.colors_group_box = _ColorsGroupBox(self, self._mapper)
        self.outline_group_box = _OutlineGroupBox(self, self._mapper)
        self.misc_group_box = _MiscGroupBox(self, self._mapper)
        self.margins_group_box = _MarginGroupBox(self, self._mapper)
        self.alignment_group_box = _AlignmentGroupBox(self, self._mapper)

        left_widget = QtWidgets.QWidget(self)
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.font_group_box)
        left_layout.addWidget(self.colors_group_box)
        left_layout.addWidget(self.outline_group_box)

        right_widget = QtWidgets.QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.misc_group_box)
        right_layout.addWidget(self.margins_group_box)
        right_layout.addWidget(self.alignment_group_box)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(left_widget)
        layout.addWidget(right_widget)

        self._connect_signals()

    def _on_selection_change(
            self,
            selected: QtCore.QItemSelection,
            _deselected: QtCore.QItemSelection
    ) -> None:
        if selected.indexes():
            self.setEnabled(True)
            self._mapper.setCurrentIndex(selected.indexes()[0].row())
        else:
            self.setEnabled(False)

    def _connect_signals(self) -> None:
        self._mapper.setSubmitPolicy(QtWidgets.QDataWidgetMapper.ManualSubmit)

        signal_mapper: T.Dict[
            QtWidgets.QWidget,
            T.Callable[[QtWidgets.QWidget], QtCore.pyqtSignal]
        ] = {
            QtWidgets.QCheckBox: lambda widget: widget.toggled,
            QtWidgets.QSpinBox: lambda widget: widget.valueChanged,
            QtWidgets.QDoubleSpinBox: lambda widget: widget.valueChanged,
            QtWidgets.QComboBox: lambda widget: widget.currentIndexChanged,
            _AlignmentGroupBox: lambda widget: widget.changed,
            bubblesub.ui.util.ColorPicker: lambda widget: widget.changed,
        }

        for column in StylesModelColumn:
            widget = self._mapper.mappedWidgetAt(column)
            if widget is None:
                continue
            for type_, get_signal in signal_mapper.items():
                if isinstance(widget, type_):
                    get_signal(widget).connect(self._submit)
                    break
            else:
                raise RuntimeError(f'Unknown widget type: "{type(widget)}"')

    def _submit(self, *_args: T.Any) -> None:
        self._mapper.submit()


class _StylesManagerDialog(QtWidgets.QDialog):
    def __init__(
            self,
            api: bubblesub.api.Api,
            main_window: QtWidgets.QMainWindow
    ) -> None:
        super().__init__(main_window)
        model = StylesModel(self, api.subs.styles)
        selection_model = QtCore.QItemSelectionModel(model)

        self._style_list = _StyleList(api, model, selection_model, self)
        self._style_editor = _StyleEditor(model, selection_model, self)
        self._style_editor.setEnabled(False)
        self._preview_box = _StylePreview(api, selection_model, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self._style_list)
        layout.addWidget(self._style_editor)
        layout.addWidget(self._preview_box)

        self.setWindowTitle('Styles manager')

    def resizeEvent(self, _event: QtGui.QResizeEvent) -> None:
        self._preview_box.update_preview()


class StylesManagerCommand(BaseCommand):
    """Opens up the style manager."""

    name = 'edit/manage-styles'
    menu_name = '&Manage styles...'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return True

    async def run(self) -> None:
        """Carry out the command."""
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        with self.api.undo.capture():
            _StylesManagerDialog(self.api, main_window).exec_()


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    cmd_api.register_core_command(StylesManagerCommand)
