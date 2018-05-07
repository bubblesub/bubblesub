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

import enchant
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ass.util
import bubblesub.ui.util


class SpellCheckHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, api: bubblesub.api.Api, *args: T.Any) -> None:
        super().__init__(*args)

        spell_check_lang = api.opt.general.spell_check
        try:
            self._dictionary = (
                enchant.Dict(spell_check_lang)
                if spell_check_lang else
                None
            )
        except enchant.errors.DictNotFoundError:
            self._dictionary = None
            api.log.warn(f'dictionary {spell_check_lang} not installed.')

        self._fmt = QtGui.QTextCharFormat()
        self._fmt.setUnderlineColor(QtCore.Qt.red)
        self._fmt.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
        self._fmt.setFontUnderline(True)

    def highlightBlock(self, text: str) -> None:
        if not self._dictionary:
            return

        for start, end, _match in bubblesub.ass.util.spell_check_ass_line(
                self._dictionary, text
        ):
            self.setFormat(start, end - start, self._fmt)


class TextEdit(QtWidgets.QPlainTextEdit):
    def __init__(
            self,
            api: bubblesub.api.Api,
            name: str,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._api = api
        try:
            font_def = self._api.opt.general.gui.fonts[name]
            if font_def:
                font = QtGui.QFont()
                font.fromString(font_def)
                self.setFont(font)
        except KeyError:
            pass

        self.setMinimumHeight(
            bubblesub.ui.util.get_text_edit_row_height(self, 2)
        )

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & QtCore.Qt.ControlModifier:
            distance = 1 if event.angleDelta().y() > 0 else -1
            new_size = self.font().pointSize() + distance
            if new_size < 5:
                return
            font = self.font()
            font.setPointSize(new_size)
            self.setFont(font)
            self._api.opt.general.gui.fonts[self._name] = (
                self.font().toString()
            )


class Bar1(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.style_edit = QtWidgets.QComboBox(self)
        self.style_edit.setEditable(True)
        self.style_edit.setMinimumWidth(200)
        self.style_edit.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        self.actor_edit = QtWidgets.QComboBox(self)
        self.actor_edit.setEditable(True)
        self.actor_edit.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        self.layer_edit = QtWidgets.QSpinBox(self)
        self.layer_edit.setMinimum(0)

        self.margin_l_edit = QtWidgets.QSpinBox(self)
        self.margin_l_edit.setMinimum(0)
        self.margin_l_edit.setMaximum(999)
        self.margin_v_edit = QtWidgets.QSpinBox(self)
        self.margin_v_edit.setMinimum(0)
        self.margin_v_edit.setMaximum(999)
        self.margin_r_edit = QtWidgets.QSpinBox(self)
        self.margin_r_edit.setMinimum(0)
        self.margin_r_edit.setMaximum(999)
        margins_layout = QtWidgets.QHBoxLayout()
        margins_layout.setSpacing(4)
        margins_layout.setContentsMargins(0, 0, 0, 0)
        margins_layout.addWidget(self.margin_l_edit)
        margins_layout.addWidget(self.margin_v_edit)
        margins_layout.addWidget(self.margin_r_edit)

        layout = QtWidgets.QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel('Style:', self), 0, 0)
        layout.addWidget(self.style_edit, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Actor:', self), 1, 0)
        layout.addWidget(self.actor_edit, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Layer:', self), 2, 0)
        layout.addWidget(self.layer_edit, 2, 1)
        layout.addWidget(QtWidgets.QLabel('Margin:', self), 3, 0)
        layout.addLayout(margins_layout, 3, 1)


class Bar2(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.start_time_edit = bubblesub.ui.util.TimeEdit(self)
        self.end_time_edit = bubblesub.ui.util.TimeEdit(self)
        self.duration_edit = bubblesub.ui.util.TimeEdit(self)
        self.comment_checkbox = QtWidgets.QCheckBox('Comment', self)

        layout = QtWidgets.QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel('Start time:', self), 0, 0)
        layout.addWidget(self.start_time_edit, 0, 1)
        layout.addWidget(QtWidgets.QLabel('End time:', self), 1, 0)
        layout.addWidget(self.end_time_edit, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Duration:', self), 2, 0)
        layout.addWidget(self.duration_edit, 2, 1)
        layout.addWidget(self.comment_checkbox, 3, 1)


class TextContainer(QtWidgets.QWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)

        self.text_edit = TextEdit(api, 'editor', self)
        self.text_edit.setTabChangesFocus(True)
        self.text_edit.highlighter = (
            SpellCheckHighlighter(api, self.text_edit.document())
        )

        self.note_edit = TextEdit(api, 'notes', self)
        self.note_edit.setTabChangesFocus(True)
        self.note_edit.setPlaceholderText('Notes')

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.note_edit)


class Editor(QtWidgets.QWidget):
    def __init__(
            self,
            api: bubblesub.api.Api,
            parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)

        self._index: T.Optional[int] = None
        self._api = api

        self.bar1 = Bar1(self)
        self.bar2 = Bar2(self)
        self.center = TextContainer(api, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.bar1)
        layout.addWidget(self.bar2)
        layout.addWidget(self.center)
        layout.setStretchFactor(self.center, 1)
        self.setEnabled(False)

        self._connect_api_signals()
        self._connect_ui_signals()

    def _fetch_selection(self, index: int) -> None:
        self._index = index
        subtitle = self._api.subs.events[index]
        self.bar1.layer_edit.setValue(subtitle.layer)
        self.bar1.margin_l_edit.setValue(subtitle.margin_left)
        self.bar1.margin_v_edit.setValue(subtitle.margin_vertical)
        self.bar1.margin_r_edit.setValue(subtitle.margin_right)
        self.bar2.start_time_edit.set_value(subtitle.start)
        self.bar2.end_time_edit.set_value(subtitle.end)
        self.bar2.duration_edit.set_value(subtitle.duration)
        self.bar2.comment_checkbox.setChecked(subtitle.is_comment)

        self.bar1.actor_edit.clear()
        self.bar1.actor_edit.addItems(
            sorted(list(set(sub.actor for sub in self._api.subs.events)))
        )
        self.bar1.actor_edit.lineEdit().setText(subtitle.actor)

        self.bar1.style_edit.clear()
        self.bar1.style_edit.addItems(
            sorted(list(set(sub.style for sub in self._api.subs.events)))
        )
        self.bar1.style_edit.lineEdit().setText(subtitle.style)

        self.center.text_edit.document().setPlainText(
            self._convert_newlines(subtitle.text)
        )
        self.center.note_edit.document().setPlainText(
            self._convert_newlines(subtitle.note)
        )
        self.setEnabled(True)

    def _convert_newlines(self, text: str) -> str:
        if self._api.opt.general.convert_newlines:
            return text.replace('\\N', '\n')
        return text

    def _clear_selection(self) -> None:
        self._index = None
        self.bar1.style_edit.lineEdit().setText('')
        self.bar1.actor_edit.lineEdit().setText('')
        self.bar1.layer_edit.setValue(0)
        self.bar1.margin_l_edit.setValue(0)
        self.bar1.margin_v_edit.setValue(0)
        self.bar1.margin_r_edit.setValue(0)
        self.bar2.start_time_edit.reset_text()
        self.bar2.end_time_edit.reset_text()
        self.bar2.duration_edit.reset_text()
        self.bar2.comment_checkbox.setChecked(False)
        self.center.text_edit.document().setPlainText('')
        self.center.note_edit.document().setPlainText('')
        self.setEnabled(False)

    def _push_selection(self) -> None:
        if not self.isEnabled():
            return
        assert self._index is not None

        self._disconnect_api_signals()
        with self._api.undo.capture():
            subtitle = self._api.subs.events[self._index]
            subtitle.begin_update()
            subtitle.start = self.bar2.start_time_edit.get_value()
            subtitle.end = self.bar2.end_time_edit.get_value()
            subtitle.style = self.bar1.style_edit.lineEdit().text()
            subtitle.actor = self.bar1.actor_edit.lineEdit().text()
            subtitle.text = (
                self.center.text_edit.toPlainText().replace('\n', r'\N')
            )
            subtitle.note = (
                self.center.note_edit.toPlainText().replace('\n', r'\N')
            )
            subtitle.layer = self.bar1.layer_edit.value()
            subtitle.margin_left = self.bar1.margin_l_edit.value()
            subtitle.margin_vertical = self.bar1.margin_v_edit.value()
            subtitle.margin_right = self.bar1.margin_r_edit.value()
            subtitle.is_comment = self.bar2.comment_checkbox.isChecked()
            subtitle.end_update()
        self._connect_api_signals()

    def _on_grid_selection_change(
            self,
            rows: T.List[int],
            _changed: bool
    ) -> None:
        self._disconnect_ui_signals()
        if len(rows) == 1:
            self._fetch_selection(rows[0])
        else:
            self._clear_selection()
        self._connect_ui_signals()

    def _on_items_insert(self, idx: int, count: int) -> None:
        if self._index is not None and self._index in range(idx, idx + count):
            self._disconnect_ui_signals()
            self._fetch_selection(self._index)
            self._connect_ui_signals()

    def _on_items_remove(self, idx: int, count: int) -> None:
        if self._index is not None and self._index in range(idx, idx + count):
            self._disconnect_ui_signals()
            self._clear_selection()
            self._connect_ui_signals()

    def _on_item_change(self, idx: int) -> None:
        if idx == self._index or idx is None:
            self._disconnect_ui_signals()
            self._fetch_selection(self._index)
            self._connect_ui_signals()

    def _on_time_end_edit(self) -> None:
        self._disconnect_ui_signals()
        start = self.bar2.start_time_edit.get_value()
        end = self.bar2.end_time_edit.get_value()
        duration = end - start
        self.bar2.duration_edit.set_value(duration)
        self._push_selection()
        self._connect_ui_signals()

    def _on_duration_edit(self) -> None:
        self._disconnect_ui_signals()
        start = self.bar2.start_time_edit.get_value()
        duration = self.bar2.duration_edit.get_value()
        end = start + duration
        self.bar2.end_time_edit.set_value(end)
        self._push_selection()
        self._connect_ui_signals()

    def _on_generic_edit(self) -> None:
        self._push_selection()

    def _connect_api_signals(self) -> None:
        self._api.subs.events.items_inserted.connect(self._on_items_insert)
        self._api.subs.events.items_removed.connect(self._on_items_remove)
        self._api.subs.events.item_changed.connect(self._on_item_change)
        self._api.subs.selection_changed.connect(
            self._on_grid_selection_change
        )

    def _disconnect_api_signals(self) -> None:
        self._api.subs.events.items_inserted.disconnect(self._on_items_insert)
        self._api.subs.events.items_removed.disconnect(self._on_items_remove)
        self._api.subs.events.item_changed.disconnect(self._on_item_change)
        self._api.subs.selection_changed.disconnect(
            self._on_grid_selection_change
        )

    # TODO: get rid of this crap

    def _connect_ui_signals(self) -> None:
        self.bar2.start_time_edit.textEdited.connect(self._on_generic_edit)
        self.bar2.end_time_edit.textEdited.connect(self._on_time_end_edit)
        self.bar2.duration_edit.textEdited.connect(self._on_duration_edit)
        self.bar1.actor_edit.editTextChanged.connect(self._on_generic_edit)
        self.bar1.style_edit.editTextChanged.connect(self._on_generic_edit)
        self.center.text_edit.textChanged.connect(self._on_generic_edit)
        self.center.note_edit.textChanged.connect(self._on_generic_edit)
        self.bar1.layer_edit.valueChanged.connect(self._on_generic_edit)
        self.bar1.margin_l_edit.valueChanged.connect(self._on_generic_edit)
        self.bar1.margin_v_edit.valueChanged.connect(self._on_generic_edit)
        self.bar1.margin_r_edit.valueChanged.connect(self._on_generic_edit)
        self.bar2.comment_checkbox.stateChanged.connect(
            self._on_generic_edit
        )

    def _disconnect_ui_signals(self) -> None:
        self.bar2.start_time_edit.textEdited.disconnect(self._on_generic_edit)
        self.bar2.end_time_edit.textEdited.disconnect(self._on_time_end_edit)
        self.bar2.duration_edit.textEdited.disconnect(self._on_duration_edit)
        self.bar1.actor_edit.editTextChanged.disconnect(self._on_generic_edit)
        self.bar1.style_edit.editTextChanged.disconnect(self._on_generic_edit)
        self.center.text_edit.textChanged.disconnect(self._on_generic_edit)
        self.center.note_edit.textChanged.disconnect(self._on_generic_edit)
        self.bar1.layer_edit.valueChanged.disconnect(self._on_generic_edit)
        self.bar1.margin_l_edit.valueChanged.disconnect(self._on_generic_edit)
        self.bar1.margin_v_edit.valueChanged.disconnect(self._on_generic_edit)
        self.bar1.margin_r_edit.valueChanged.disconnect(self._on_generic_edit)
        self.bar2.comment_checkbox.stateChanged.disconnect(
            self._on_generic_edit
        )
