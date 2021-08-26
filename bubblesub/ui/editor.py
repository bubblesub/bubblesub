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

from typing import Any, Optional, Union

from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtGui import (
    QFont,
    QKeyEvent,
    QSyntaxHighlighter,
    QTextCharFormat,
    QWheelEvent,
)
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSpinBox,
    QWidget,
)

from bubblesub.api import Api
from bubblesub.ass_util import spell_check_ass_line
from bubblesub.spell_check import SpellCheckerError, create_spell_checker
from bubblesub.ui.model.events import AssEventsModel, AssEventsModelColumn
from bubblesub.ui.themes import ThemeManager
from bubblesub.ui.time_edit import TimeEdit
from bubblesub.ui.util import (
    ImmediateDataWidgetMapper,
    get_text_edit_row_height,
)
from bubblesub.ui.vim_text_edit import VimTextEdit


class SpellCheckHighlighter(QSyntaxHighlighter):
    def __init__(self, api: Api, *args: Any) -> None:
        super().__init__(*args)
        self._api = api
        self._fmt = QTextCharFormat()
        self._fmt.setUnderlineColor(Qt.GlobalColor.red)
        self._fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        self._fmt.setFontUnderline(True)

        self._api.subs.script_info.changed.subscribe(
            lambda _event: self.reset()
        )

        self.reset()

    def reset(self) -> None:
        spell_check_lang = (
            self._api.subs.language or self._api.cfg.opt["gui"]["spell_check"]
        )
        try:
            self._spell_checker = (
                create_spell_checker(spell_check_lang)
                if spell_check_lang
                else None
            )
        except SpellCheckerError as ex:
            self._spell_checker = None
            self._api.log.warn(str(ex))

    def highlightBlock(self, text: str) -> None:
        if not self._spell_checker:
            return

        for start, end, _match in spell_check_ass_line(
            self._spell_checker, text
        ):
            self.setFormat(start, end - start, self._fmt)


class TextEdit(VimTextEdit):
    def __init__(self, api: Api, parent: QWidget) -> None:
        super().__init__(parent)
        self._z_mode = False
        self._api = api
        try:
            font_def = self._api.cfg.opt["gui"]["fonts"][self.objectName()]
        except KeyError:
            pass
        else:
            if font_def:
                font = QFont()
                font.fromString(font_def)
                self.setFont(font)

        self.setMinimumHeight(get_text_edit_row_height(self, 2))
        self.vim_mode_enabled = self._api.cfg.opt["basic"]["vim_mode"]

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
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

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.vim_mode_enabled and self._nvim:
            response = self._nvim.request("nvim_get_mode")
            mode = response["mode"]
            blocking = response["blocking"]

            if self._z_mode and event.text() == "p":
                self._api.cmd.run_cmdline("play-region -s=a.s -e=a.e")
                self._z_mode = False

            elif not blocking:
                if mode == "n" and event.text() == "z":
                    self._z_mode = True
                else:
                    self._z_mode = False

                row, _col = self._nvim.current.window.cursor
                if mode == "n" and event.text() == "k" and row == 1:
                    self._api.cmd.run_cmdline("sub-select one-above")
                    return
                if (
                    mode == "n"
                    and event.text() == "j"
                    and row == len(self._nvim.current.buffer)
                ):
                    self._api.cmd.run_cmdline("sub-select one-below")
                    return

        super().keyPressEvent(event)


class Editor(QWidget):
    def __init__(
        self, api: Api, theme_mgr: ThemeManager, parent: QWidget
    ) -> None:
        # pylint: disable=too-many-statements
        super().__init__(parent)
        self._api = api
        self._theme_mgr = theme_mgr

        self.style_edit = QComboBox(self)
        self.style_edit.setEditable(True)
        self.style_edit.setMinimumWidth(200)
        self.style_edit.setInsertPolicy(QComboBox.NoInsert)
        self.style_edit.setObjectName("style-editor")

        self.actor_edit = QComboBox(self)
        self.actor_edit.setEditable(True)
        self.actor_edit.setInsertPolicy(QComboBox.NoInsert)
        self.actor_edit.setObjectName("actor-editor")

        self.layer_edit = QSpinBox(self)
        self.layer_edit.setObjectName("layer-editor")
        self.layer_edit.setMinimum(0)

        self.margin_l_edit = QSpinBox(self)
        self.margin_l_edit.setObjectName("margin-left-editor")
        self.margin_l_edit.setMinimum(0)
        self.margin_l_edit.setMaximum(999)

        self.margin_v_edit = QSpinBox(self)
        self.margin_v_edit.setObjectName("margin-vertical-editor")
        self.margin_v_edit.setMinimum(0)
        self.margin_v_edit.setMaximum(999)

        self.margin_r_edit = QSpinBox(self)
        self.margin_r_edit.setObjectName("margin-right-editor")
        self.margin_r_edit.setMinimum(0)
        self.margin_r_edit.setMaximum(999)

        self.start_time_edit = TimeEdit(self)
        self.start_time_edit.setObjectName("start-time-editor")

        self.end_time_edit = TimeEdit(self)
        self.end_time_edit.setObjectName("end-time-editor")

        self.duration_edit = TimeEdit(self)
        self.duration_edit.setObjectName("duration-editor")
        self.duration_edit.setDisabled(True)

        self.comment_checkbox = QCheckBox("Comment", self)
        self.comment_checkbox.setObjectName("comment-checkbox")

        self.text_edit = TextEdit(api, self)
        self.text_edit.setTabChangesFocus(True)
        self.text_edit.setObjectName("text-editor")

        self.note_edit = TextEdit(api, self)
        self.note_edit.setTabChangesFocus(True)
        self.note_edit.setPlaceholderText("Notes")
        self.note_edit.setObjectName("note-editor")

        margins_layout = QHBoxLayout()
        margins_layout.setSpacing(4)
        margins_layout.setContentsMargins(0, 0, 0, 0)
        margins_layout.addWidget(self.margin_l_edit)
        margins_layout.addWidget(self.margin_v_edit)
        margins_layout.addWidget(self.margin_r_edit)

        bar_layout = QGridLayout()
        bar_layout.setSpacing(4)
        bar_layout.setContentsMargins(0, 0, 0, 0)

        widget_map: set[tuple[int, int, str, Union[QWidget, QLayout]]] = {
            (0, 0, "Style:", self.style_edit),
            (1, 0, "Actor:", self.actor_edit),
            (2, 0, "Layer:", self.layer_edit),
            (3, 0, "Margin:", margins_layout),
            (0, 1, "Start time:", self.start_time_edit),
            (1, 1, "End time:", self.end_time_edit),
            (2, 1, "Duration:", self.duration_edit),
            (3, 1, "", self.comment_checkbox),
        }
        for row, column, label, widget in widget_map:
            if label:
                bar_layout.addWidget(QLabel(label, self), row, column * 2)
            if isinstance(widget, QLayout):
                bar_layout.addLayout(widget, row, column * 2 + 1)
            else:
                bar_layout.addWidget(widget, row, column * 2 + 1)

        layout = QHBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar_layout)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.note_edit)
        layout.setStretchFactor(self.text_edit, 1)
        layout.setStretchFactor(self.note_edit, 1)
        self.setEnabled(False)

        api.subs.loaded.connect(self._on_subs_load)
        api.subs.selection_changed.connect(self._on_selection_change)

        self._data_widget_mapper: Optional[ImmediateDataWidgetMapper] = None

        app = QApplication.instance()
        assert app
        app.installEventFilter(self)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if isinstance(source, QWidget) and self.isAncestorOf(source):
            if event.type() == QEvent.Type.FocusOut:
                self._api.undo.push()
        return False

    def _on_subs_load(self) -> None:
        self._data_widget_mapper = ImmediateDataWidgetMapper(
            model=AssEventsModel(self._api, self._theme_mgr, self),
            signal_map={TextEdit: "textChanged"},
        )
        widget_map: set[tuple[AssEventsModelColumn, QWidget]] = {
            (AssEventsModelColumn.START, self.start_time_edit),
            (AssEventsModelColumn.END, self.end_time_edit),
            (AssEventsModelColumn.LONG_DURATION, self.duration_edit),
            (AssEventsModelColumn.LAYER, self.layer_edit),
            (AssEventsModelColumn.ACTOR, self.actor_edit),
            (AssEventsModelColumn.ASS_STYLE, self.style_edit),
            (AssEventsModelColumn.MARGIN_VERTICAL, self.margin_v_edit),
            (AssEventsModelColumn.MARGIN_LEFT, self.margin_l_edit),
            (AssEventsModelColumn.MARGIN_RIGHT, self.margin_r_edit),
            (AssEventsModelColumn.IS_COMMENT, self.comment_checkbox),
            (AssEventsModelColumn.TEXT, self.text_edit),
            (AssEventsModelColumn.NOTE, self.note_edit),
        }
        for column, widget in widget_map:
            self._data_widget_mapper.add_mapping(widget, column)

        self.text_edit.highlighter = SpellCheckHighlighter(
            self._api, self.text_edit.document()
        )

    def _on_selection_change(
        self, selected: list[int], _changed: bool
    ) -> None:
        if not self._data_widget_mapper:
            return

        self._api.undo.push()

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
            sorted(list(set(sub.style_name for sub in self._api.subs.events)))
        )
        self.style_edit.blockSignals(False)

        self.setEnabled(True)
        self._data_widget_mapper.set_current_index(selected[0])
        self.text_edit.reset()
        self.note_edit.reset()
