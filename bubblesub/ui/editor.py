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

import contextlib
import typing as T

import enchant
from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.ass.util import spell_check_ass_line
from bubblesub.ui.model.events import AssEventsModel, AssEventsModelColumn
from bubblesub.ui.util import (
    ImmediateDataWidgetMapper,
    TimeEdit,
    get_text_edit_row_height,
)


class SpellCheckHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, api: Api, *args: T.Any) -> None:
        super().__init__(*args)

        spell_check_lang = api.cfg.opt["gui"]["spell_check"]
        try:
            self._dictionary = (
                enchant.Dict(spell_check_lang) if spell_check_lang else None
            )
        except enchant.errors.DictNotFoundError:
            self._dictionary = None
            api.log.warn(f"dictionary {spell_check_lang} not installed")

        self._fmt = QtGui.QTextCharFormat()
        self._fmt.setUnderlineColor(QtCore.Qt.red)
        self._fmt.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
        self._fmt.setFontUnderline(True)

    def highlightBlock(self, text: str) -> None:
        if not self._dictionary:
            return

        for start, end, _match in spell_check_ass_line(self._dictionary, text):
            self.setFormat(start, end - start, self._fmt)


class TextEdit(QtWidgets.QPlainTextEdit):
    def __init__(
        self, api: Api, parent: QtWidgets.QWidget, **kwargs: T.Any
    ) -> None:
        super().__init__(parent, **kwargs)
        self._api = api
        try:
            font_def = self._api.cfg.opt["gui"]["fonts"][self.objectName()]
        except KeyError:
            pass
        else:
            if font_def:
                font = QtGui.QFont()
                font.fromString(font_def)
                self.setFont(font)

        self.setMinimumHeight(get_text_edit_row_height(self, 2))

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & QtCore.Qt.ControlModifier:
            distance = 1 if event.angleDelta().y() > 0 else -1
            new_size = self.font().pointSize() + distance
            if new_size < 5:
                return
            font = self.font()
            font.setPointSize(new_size)
            self.setFont(font)
            self._api.cfg.opt["gui"]["fonts"][
                self.objectName()
            ] = self.font().toString()


class Editor(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self._api = api

        self.style_edit = QtWidgets.QComboBox(
            self,
            editable=True,
            minimumWidth=200,
            insertPolicy=QtWidgets.QComboBox.NoInsert,
            objectName="style-editor",
        )

        self.actor_edit = QtWidgets.QComboBox(
            self,
            editable=True,
            insertPolicy=QtWidgets.QComboBox.NoInsert,
            objectName="actor-editor",
        )

        self.layer_edit = QtWidgets.QSpinBox(
            self, minimum=0, objectName="layer-editor"
        )

        self.margin_l_edit = QtWidgets.QSpinBox(
            self, minimum=0, maximum=999, objectName="margin-left-editor"
        )

        self.margin_v_edit = QtWidgets.QSpinBox(
            self, minimum=0, maximum=999, objectName="margin-vertical-editor"
        )

        self.margin_r_edit = QtWidgets.QSpinBox(
            self, minimum=0, maximum=999, objectName="margin-right-editor"
        )

        self.start_time_edit = TimeEdit(self, objectName="start-time-editor")
        self.end_time_edit = TimeEdit(self, objectName="end-time-editor")
        self.duration_edit = TimeEdit(self, objectName="duration-editor")

        self.comment_checkbox = QtWidgets.QCheckBox(
            "Comment", self, objectName="comment-checkbox"
        )

        self.text_edit = TextEdit(
            api, self, tabChangesFocus=True, objectName="text-editor"
        )
        self.text_edit.highlighter = SpellCheckHighlighter(
            api, self.text_edit.document()
        )

        self.note_edit = TextEdit(
            api,
            self,
            tabChangesFocus=True,
            placeholderText="Notes",
            objectName="note-editor",
        )

        margins_layout = QtWidgets.QHBoxLayout(spacing=4)
        margins_layout.setContentsMargins(0, 0, 0, 0)
        margins_layout.addWidget(self.margin_l_edit)
        margins_layout.addWidget(self.margin_v_edit)
        margins_layout.addWidget(self.margin_r_edit)

        bar_layout = QtWidgets.QGridLayout(spacing=4)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        for row, column, label, widget in {
            (0, 0, "Style:", self.style_edit),
            (1, 0, "Actor:", self.actor_edit),
            (2, 0, "Layer:", self.layer_edit),
            (3, 0, "Margin:", margins_layout),
            (0, 1, "Start time:", self.start_time_edit),
            (1, 1, "End time:", self.end_time_edit),
            (2, 1, "Duration:", self.duration_edit),
            (3, 1, "", self.comment_checkbox),
        }:
            if label:
                bar_layout.addWidget(
                    QtWidgets.QLabel(label, self), row, column * 2
                )
            if isinstance(widget, QtWidgets.QLayout):
                bar_layout.addLayout(widget, row, column * 2 + 1)
            else:
                bar_layout.addWidget(widget, row, column * 2 + 1)

        layout = QtWidgets.QHBoxLayout(self, spacing=6)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar_layout)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.note_edit)
        layout.setStretchFactor(self.text_edit, 1)
        layout.setStretchFactor(self.note_edit, 1)
        self.setEnabled(False)

        self._data_widget_mapper = ImmediateDataWidgetMapper(
            model=AssEventsModel(
                self,
                api,
                convert_newlines=self._api.cfg.opt["gui"]["convert_newlines"],
            ),
            signal_map={TextEdit: "textChanged"},
            submit_wrapper=self._submit_wrapper,
        )
        for column, widget in {
            (AssEventsModelColumn.Start, self.start_time_edit),
            (AssEventsModelColumn.End, self.end_time_edit),
            (AssEventsModelColumn.LongDuration, self.duration_edit),
            (AssEventsModelColumn.Layer, self.layer_edit),
            (AssEventsModelColumn.Actor, self.actor_edit),
            (AssEventsModelColumn.AssStyle, self.style_edit),
            (AssEventsModelColumn.MarginVertical, self.margin_v_edit),
            (AssEventsModelColumn.MarginLeft, self.margin_l_edit),
            (AssEventsModelColumn.MarginRight, self.margin_r_edit),
            (AssEventsModelColumn.IsComment, self.comment_checkbox),
            (AssEventsModelColumn.Text, self.text_edit),
            (AssEventsModelColumn.Note, self.note_edit),
        }:
            self._data_widget_mapper.add_mapping(widget, column)

        api.subs.selection_changed.connect(self._on_selection_change)

    @contextlib.contextmanager
    def _submit_wrapper(self) -> T.Generator:
        with self._api.undo.capture():
            yield

    def _on_selection_change(
        self, selected: T.List[int], _changed: bool
    ) -> None:
        if len(selected) != 1:
            self.setEnabled(False)
            self._data_widget_mapper.set_current_index(None)
            return

        self.actor_edit.blockSignals(True)
        self.actor_edit.clear()
        self.actor_edit.addItems(
            sorted(list(set(sub.actor for sub in self._api.subs.events)))
        )
        self.actor_edit.blockSignals(False)

        self.style_edit.blockSignals(True)
        self.style_edit.clear()
        self.style_edit.addItems(
            sorted(list(set(sub.style for sub in self._api.subs.events)))
        )
        self.style_edit.blockSignals(False)

        self.setEnabled(True)
        self._data_widget_mapper.set_current_index(selected[0])
