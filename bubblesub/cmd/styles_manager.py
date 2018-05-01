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
import bubblesub.ui.ass_renderer
import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand
from bubblesub.ui.model.styles import StylesModel, StylesModelColumn


class StylePreview(QtWidgets.QGroupBox):
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
        bubblesub.ui.util.set_text_edit_height(self._editor, 2)

        self._preview_box = QtWidgets.QLabel(self)
        self._preview_box.setLineWidth(1)
        self._preview_box.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._preview_box.setFrameShadow(QtWidgets.QFrame.Sunken)
        self._preview_box.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Ignored
        ))

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._editor)
        layout.addWidget(self._preview_box)

        self._update_preview()
        self._editor.textChanged.connect(self._on_text_change)
        api.subs.styles.item_changed.connect(self._update_preview)
        api.subs.styles.items_inserted.connect(self._update_preview)
        api.subs.styles.items_removed.connect(self._update_preview)
        selection_model.selectionChanged.connect(self._update_preview)

    def _on_text_change(self) -> None:
        self._update_preview()
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

    def _update_preview(self) -> None:
        selected_style = self._selected_style
        if not selected_style:
            self._preview_box.clear()
            return

        resolution = (self._preview_box.width(), self._preview_box.height())

        fake_style_list = bubblesub.ass.style.StyleList()
        fake_style_list.insert(0, [copy(selected_style)])
        fake_style_list.get(0).name = 'Default'

        fake_event_list = bubblesub.ass.event.EventList()
        fake_event_list.insert_one(
            0,
            start=0,
            end=1000,
            text=self._editor.toPlainText().replace('\n', '\\N'),
            style='Default'
        )

        track = self._ctx.make_track()
        track.populate(fake_style_list, fake_event_list, play_res=resolution)

        self._renderer.set_all_sizes(resolution)
        imgs = self._renderer.render_frame(track, now=0)

        image = PIL.Image.new(mode='RGBA', size=resolution)
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


class StyleList(QtWidgets.QWidget):
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
            for line in self._api.subs.lines:
                if line.style == old_name:
                    line.style = new_name

        self._styles_list_view.selectionModel().select(
            self._styles_list_view.model().index(idx, 0),
            QtCore.QItemSelectionModel.Select
        )


class FontGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__('Font', parent)
        self.font_name_edit = QtWidgets.QComboBox(self)
        self.font_name_edit.setEditable(False)
        self.font_name_edit.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred
        ))
        self.font_name_edit.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.font_size_edit = QtWidgets.QSpinBox(self)
        self.font_size_edit.setMinimum(0)
        self.bold_checkbox = QtWidgets.QCheckBox('Bold', self)
        self.italic_checkbox = QtWidgets.QCheckBox('Italic', self)
        self.underline_checkbox = QtWidgets.QCheckBox('Underline', self)
        self.strike_out_checkbox = QtWidgets.QCheckBox('Strike-out', self)

        all_fonts = QtGui.QFontDatabase().families()
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


class AlignmentGroupBox(QtWidgets.QGroupBox):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget) -> None:
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

    def get_value(self) -> int:
        for idx, radio_button in self.radio_buttons.items():
            if radio_button.isChecked():
                return idx
        return -1

    def set_value(self, value: int) -> None:
        if value in self.radio_buttons:
            self.radio_buttons[value].setChecked(True)

    value = QtCore.pyqtProperty(int, get_value, set_value)


class ColorsGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
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


class OutlineGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
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


class MarginGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
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


class MiscGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
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


class StyleEditor(QtWidgets.QWidget):
    def __init__(
            self,
            model: StylesModel,
            selection_model: QtCore.QItemSelectionModel,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self._model = model
        selection_model.selectionChanged.connect(self._on_selection_change)

        self.font_group_box = FontGroupBox(self)
        self.colors_group_box = ColorsGroupBox(self)
        self.outline_group_box = OutlineGroupBox(self)
        self.misc_group_box = MiscGroupBox(self)
        self.margins_group_box = MarginGroupBox(self)
        self.alignment_group_box = AlignmentGroupBox(self)

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

        mapping = {
            StylesModelColumn.FontName:
                self.font_group_box.font_name_edit,
            StylesModelColumn.FontSize:
                self.font_group_box.font_size_edit,
            StylesModelColumn.Bold:
                self.font_group_box.bold_checkbox,
            StylesModelColumn.Italic:
                self.font_group_box.italic_checkbox,
            StylesModelColumn.Underline:
                self.font_group_box.underline_checkbox,
            StylesModelColumn.StrikeOut:
                self.font_group_box.strike_out_checkbox,
            StylesModelColumn.PrimaryColor:
                (self.colors_group_box.primary_color_button, b'color'),
            StylesModelColumn.SecondaryColor:
                (self.colors_group_box.secondary_color_button, b'color'),
            StylesModelColumn.BackColor:
                (self.colors_group_box.back_color_button, b'color'),
            StylesModelColumn.OutlineColor:
                (self.colors_group_box.outline_color_button, b'color'),
            StylesModelColumn.ShadowWidth:
                self.outline_group_box.shadow_width_edit,
            StylesModelColumn.OutlineWidth:
                self.outline_group_box.outline_width_edit,
            StylesModelColumn.ScaleX:
                self.misc_group_box.scale_x_edit,
            StylesModelColumn.ScaleY:
                self.misc_group_box.scale_y_edit,
            StylesModelColumn.Angle:
                self.misc_group_box.angle_edit,
            StylesModelColumn.Spacing:
                self.misc_group_box.spacing_edit,
            StylesModelColumn.MarginLeft:
                self.margins_group_box.margin_left_edit,
            StylesModelColumn.MarginRight:
                self.margins_group_box.margin_right_edit,
            StylesModelColumn.MarginVertical:
                self.margins_group_box.margin_vertical_edit,
            StylesModelColumn.Alignment:
                (self.alignment_group_box, b'value'),
        }

        self.mapper = QtWidgets.QDataWidgetMapper()
        self.mapper.setModel(self._model)
        for column_idx, widget in mapping.items():
            if isinstance(widget, tuple):
                widget, class_property = widget
                self.mapper.addMapping(widget, column_idx, class_property)
            else:
                self.mapper.addMapping(widget, column_idx)

        self._connect_signals()

    def _on_selection_change(
            self,
            selected: QtCore.QItemSelection,
            _deselected: QtCore.QItemSelection
    ) -> None:
        if selected.indexes():
            self.setEnabled(True)
            self.mapper.setCurrentIndex(selected.indexes()[0].row())
        else:
            self.setEnabled(False)

    def _connect_signals(self) -> None:
        self.mapper.setSubmitPolicy(QtWidgets.QDataWidgetMapper.ManualSubmit)
        for widget in [
                self.font_group_box.font_name_edit
        ]:
            widget.currentIndexChanged.connect(self._submit)

        for widget in [
                self.colors_group_box.primary_color_button,
                self.colors_group_box.secondary_color_button,
                self.colors_group_box.back_color_button,
                self.colors_group_box.outline_color_button,
                self.alignment_group_box,
        ]:
            widget.changed.connect(self._submit)

        for widget in [
                self.font_group_box.font_size_edit,
                self.outline_group_box.shadow_width_edit,
                self.outline_group_box.outline_width_edit,
                self.misc_group_box.scale_x_edit,
                self.misc_group_box.scale_y_edit,
                self.misc_group_box.angle_edit,
                self.misc_group_box.spacing_edit,
                self.margins_group_box.margin_left_edit,
                self.margins_group_box.margin_right_edit,
                self.margins_group_box.margin_vertical_edit,
        ]:
            widget.valueChanged.connect(self._submit)

        for widget in [
                self.font_group_box.bold_checkbox,
                self.font_group_box.italic_checkbox,
                self.font_group_box.underline_checkbox,
                self.font_group_box.strike_out_checkbox,
        ]:
            widget.toggled.connect(self._submit)

    def _submit(self, *_args: T.Any) -> None:
        self.mapper.submit()


class StylesManagerDialog(QtWidgets.QDialog):
    def __init__(
            self,
            api: bubblesub.api.Api,
            main_window: QtWidgets.QMainWindow
    ) -> None:
        super().__init__(main_window)
        model = StylesModel(self, api.subs.styles)
        selection_model = QtCore.QItemSelectionModel(model)

        self._style_list = StyleList(api, model, selection_model, self)
        self._style_editor = StyleEditor(model, selection_model, self)
        self._style_editor.setEnabled(False)
        self._preview_box = StylePreview(api, selection_model, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self._style_list)
        layout.addWidget(self._style_editor)
        layout.addWidget(self._preview_box)


class StylesManagerCommand(CoreCommand):
    name = 'edit/manage-styles'
    menu_name = '&Manage styles...'

    @property
    def is_enabled(self) -> bool:
        return True

    async def run(self) -> None:
        async def run(
                api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> None:
            with self.api.undo.capture():
                StylesManagerDialog(api, main_window).exec_()

        await self.api.gui.exec(run)
