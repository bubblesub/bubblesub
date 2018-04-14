import atexit
import locale
import mpv
import tempfile
import typing as T
from copy import copy
from pathlib import Path

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ass.file
import bubblesub.ass.style
import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand
from bubblesub.ui.styles_model import StylesModel, StylesModelColumn


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

        self._preview_box = QtWidgets.QFrame(self)
        self._preview_box.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        ))

        self._slider = QtWidgets.QSlider(self)
        self._slider.setOrientation(QtCore.Qt.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(api.media.max_pts)

        self._text_box = QtWidgets.QPlainTextEdit(self)
        self._text_box.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum
        ))
        self._text_box.setFixedHeight(100)
        if self._api.subs.selected_lines:
            self._text_box.document().setPlainText(
                self._api.subs.selected_lines[0].text
            )

        locale.setlocale(locale.LC_NUMERIC, 'C')
        self._mpv = mpv.Context()
        self._mpv.set_log_level('v')
        self._mpv.set_option('config', False)
        self._mpv.set_option('quiet', False)
        self._mpv.set_option('msg-level', 'all=error')
        self._mpv.set_option('osc', False)
        self._mpv.set_option('osd-bar', False)
        self._mpv.set_option('cursor-autohide', 'no')
        self._mpv.set_option('input-cursor', False)
        self._mpv.set_option('input-vo-keyboard', False)
        self._mpv.set_option('input-default-bindings', False)
        self._mpv.set_option('ytdl', False)
        self._mpv.set_option('sub-auto', False)
        self._mpv.set_option('audio-file-auto', False)
        self._mpv.set_option('vo', 'opengl')
        self._mpv.set_option('pause', True)
        self._mpv.set_option('idle', True)
        self._mpv.set_option('sid', False)
        self._mpv.set_option('wid', str(int(self._preview_box.winId())))
        self._mpv.set_option('video-sync', 'display-vdrop')
        self._mpv.set_option('keepaspect', True)
        self._mpv.set_option('hwdec', 'auto')
        self._mpv.set_option('stop-playback-on-init-failure', False)
        self._mpv.set_option('keep-open', True)
        self._mpv.set_wakeup_callback(self._mpv_event_handler)
        self._mpv.initialize()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._preview_box)
        layout.addWidget(self._slider)
        layout.addWidget(self._text_box)

        self._tmp_subs_path = Path(tempfile.mkstemp(suffix='.ass')[1])
        atexit.register(self._tmp_subs_path.unlink)
        self._ass_file = bubblesub.ass.file.AssFile()
        self._save_subs()

        self._mpv.command('loadfile', str(api.media.path))
        self._mpv_ready = False

        self._slider.valueChanged.connect(self._on_slider_move)
        self._text_box.textChanged.connect(self._on_text_change)
        api.subs.styles.item_changed.connect(self._on_styles_change)
        api.subs.styles.items_inserted.connect(self._on_styles_change)
        api.subs.styles.items_removed.connect(self._on_styles_change)
        selection_model.selectionChanged.connect(self._on_selection_change)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(640, 480)

    def _mpv_event_handler(self) -> None:
        while self._mpv:
            event = self._mpv.wait_event(.01)
            if event.id == mpv.Events.none:
                break
            elif event.id == mpv.Events.file_loaded:
                self._mpv_loaded()

    def _mpv_loaded(self) -> None:
        self._mpv_ready = True
        self._mpv.set_property('pause', True)
        self._mpv.command('sub_add', str(self._tmp_subs_path))
        self._slider.setValue(self._api.media.current_pts)

    def _save_subs(self) -> None:
        if self._selection_model.selectedIndexes():
            row = self._selection_model.selectedIndexes()[0].row()
            style = self._api.subs.styles[row]
            style_copy = copy(style)
            style_copy.name = 'Default'
            self._ass_file.styles.clear()
            self._ass_file.styles.insert(0, [style_copy])

        self._ass_file.events.clear()
        self._ass_file.events.insert_one(
            0,
            start=0,
            end=self._api.media.max_pts,
            style='Default',
            text=self._text_box.toPlainText()
        )

        self._ass_file.info = self._api.subs.info
        with self._tmp_subs_path.open('w') as handle:
            self._ass_file.write_ass(handle)

    def _refresh_subs(self) -> None:
        if self._mpv_ready:
            try:
                self._save_subs()
                self._mpv.command('sub_reload')
            except Exception as ex:
                print(ex)

    def _on_selection_change(
            self,
            _selected: QtCore.QItemSelection,
            _deselected: QtCore.QItemSelection
    ) -> None:
        self._refresh_subs()

    def _on_styles_change(self) -> None:
        self._refresh_subs()

    def _on_text_change(self) -> None:
        self._refresh_subs()

    def _on_slider_move(self, value: int) -> None:
        try:
            self._mpv.command('seek', str(value / 1000), 'absolute+exact')
        except Exception as ex:
            print(ex)


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
            for style in self._api.subs.styles.items:
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
            for line in self._api.subs.lines.items:
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
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.addWidget(QtWidgets.QLabel('Name:', self), 0, 0)
        layout.addWidget(self.font_name_edit, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Size:', self), 1, 0)
        layout.addWidget(self.font_size_edit, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Style:', self), 2, 0)
        layout.addWidget(self.bold_checkbox, 2, 1)
        layout.addWidget(self.italic_checkbox, 3, 1)
        layout.addWidget(self.underline_checkbox, 4, 1)
        layout.addWidget(self.strike_out_checkbox, 5, 1)


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
        self.outline_width_edit.setMinimum(999)
        self.outline_width_edit.setMaximum(999)
        self.shadow_width_edit = QtWidgets.QDoubleSpinBox(self)
        self.shadow_width_edit.setMinimum(999)
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
        self.margins_group_box = MarginGroupBox(self)
        self.misc_group_box = MiscGroupBox(self)
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
        model = StylesModel(api)
        selection_model = QtCore.QItemSelectionModel(model)

        self._style_list = StyleList(api, model, selection_model, self)
        self._style_editor = StyleEditor(model, selection_model, self)
        self._preview_box = (
            StylePreview(api, selection_model, self)
            if api.media.path else
            None
        )

        self._style_editor.setEnabled(False)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self._style_list)
        layout.addWidget(self._style_editor)
        if self._preview_box:
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
