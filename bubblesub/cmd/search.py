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

import abc
import argparse
import enum
import re
from typing import Any, Optional, cast

from ass_parser import AssEvent
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.ui.util import (
    Dialog,
    async_dialog_exec,
    async_slot,
    show_notice,
)

MAX_HISTORY_ENTRIES = 25


class SearchMode(enum.IntEnum):
    """Search mode in subtitles grid."""

    TEXT = 1
    NOTE = 2
    ACTOR = 3
    STYLE = 4


def _create_search_regex(
    text: str, case_sensitive: bool, use_regexes: bool
) -> re.Pattern[str]:
    return re.compile(
        text if use_regexes else re.escape(text),
        flags=0 if case_sensitive else re.I,
    )


class _SearchModeHandler(abc.ABC):
    def __init__(self, main_window: QMainWindow) -> None:
        self.main_window = main_window

    @abc.abstractmethod
    def get_subject_text(self, sub: AssEvent) -> str:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def set_subject_text(self, sub: AssEvent, value: str) -> None:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_subject_widget_name(self) -> str:
        raise NotImplementedError("not implemented")

    def get_subject_widget(self) -> QWidget:
        widget = self.main_window.findChild(
            QWidget, self.get_subject_widget_name()
        )
        if isinstance(widget, QComboBox):
            widget = widget.lineEdit()
        return widget

    def select_text_on_widget(
        self, selection_start: int, selection_end: int
    ) -> None:
        widget = self.get_subject_widget()
        if isinstance(widget, QPlainTextEdit):
            cursor = widget.textCursor()
            cursor.setPosition(selection_start)
            cursor.setPosition(selection_end, QTextCursor.KeepAnchor)
            widget.setTextCursor(cursor)
        elif isinstance(widget, QLineEdit):
            widget.setSelection(
                selection_start, selection_end - selection_start
            )
        else:
            raise AssertionError(f"unknown search widget type ({type(widget)}")
        widget.setFocus()

    def get_selection_from_widget(self) -> tuple[int, int]:
        widget = self.get_subject_widget()
        if isinstance(widget, QPlainTextEdit):
            cursor = widget.textCursor()
            return (cursor.selectionStart(), cursor.selectionEnd())
        if isinstance(widget, QLineEdit):
            return (
                widget.selectionStart(),
                widget.selectionStart() + len(widget.selectedText()),
            )
        raise AssertionError(f"unknown search widget type ({type(widget)})")

    def get_widget_text(self) -> str:
        widget = self.get_subject_widget()
        if isinstance(widget, QPlainTextEdit):
            return cast(str, widget.toPlainText())
        if isinstance(widget, QLineEdit):
            return widget.text()
        raise AssertionError(f"unknown search widget type ({type(widget)})")

    def set_widget_text(self, text: str) -> None:
        widget = self.get_subject_widget()
        if isinstance(widget, QPlainTextEdit):
            widget.document().setPlainText(text)
        if isinstance(widget, QLineEdit):
            widget.setText(text)
        else:
            raise AssertionError(
                f"unknown search widget type ({type(widget)})"
            )


class _TextSearchModeHandler(_SearchModeHandler):
    def get_subject_text(self, sub: AssEvent) -> str:
        return sub.text.replace("\\N", "\n")

    def set_subject_text(self, sub: AssEvent, value: str) -> None:
        sub.text = value.replace("\n", "\\N")

    def get_subject_widget_name(self) -> QWidget:
        return "text-editor"


class _NoteSearchModeHandler(_SearchModeHandler):
    def get_subject_text(self, sub: AssEvent) -> str:
        return sub.note.replace("\\N", "\n")

    def set_subject_text(self, sub: AssEvent, value: str) -> None:
        sub.note = value.replace("\n", "\\N")

    def get_subject_widget_name(self) -> QWidget:
        return "note-editor"


class _ActorSearchModeHandler(_SearchModeHandler):
    def get_subject_text(self, sub: AssEvent) -> str:
        return sub.actor

    def set_subject_text(self, sub: AssEvent, value: str) -> None:
        sub.actor = value

    def get_subject_widget_name(self) -> QWidget:
        return "actor-editor"


class _StyleSearchModeHandler(_SearchModeHandler):
    def get_subject_text(self, sub: AssEvent) -> str:
        return sub.style_name

    def set_subject_text(self, sub: AssEvent, value: str) -> None:
        sub.style = value

    def get_subject_widget_name(self) -> QWidget:
        return "style-editor"


_HANDLERS: dict[SearchMode, type[_SearchModeHandler]] = {
    SearchMode.TEXT: _TextSearchModeHandler,
    SearchMode.NOTE: _NoteSearchModeHandler,
    SearchMode.ACTOR: _ActorSearchModeHandler,
    SearchMode.STYLE: _StyleSearchModeHandler,
}


def _narrow_match(
    handler: _SearchModeHandler,
    matches: list[re.Match[str]],
    idx: int,
    selected_idx: Optional[int],
    reverse: bool,
) -> Optional[re.Match[str]]:
    if idx == selected_idx:
        selection_start, selection_end = handler.get_selection_from_widget()
        if selection_end == selection_start:
            return None if reverse else matches[0]

        if reverse:
            for match in reversed(matches):
                if match.start() < selection_start:
                    return match
        else:
            for match in matches:
                if match.end() > selection_end:
                    return match

        return None

    return matches[-1] if reverse else matches[0]


def _search(
    api: Api,
    handler: _SearchModeHandler,
    regex: re.Pattern[str],
    reverse: bool,
) -> bool:
    num_lines = len(api.subs.events)
    if not api.subs.has_selection:
        selected_idx = None
        iterator = list(range(num_lines))
        if reverse:
            iterator.reverse()
    else:
        selected_idx = api.subs.selected_indexes[0]
        mul = -1 if reverse else 1
        iterator = list(
            (selected_idx + mul * i) % num_lines for i in range(num_lines)
        )

    for idx in iterator:
        subject = handler.get_subject_text(api.subs.events[idx])
        matches = list(re.finditer(regex, subject))
        if not matches:
            continue

        final_match = _narrow_match(
            handler, matches, idx, selected_idx, reverse
        )

        if not final_match:
            continue

        api.subs.selected_indexes = [idx]

        handler.select_text_on_widget(final_match.start(), final_match.end())
        return True

    return False


def _replace_selection(handler: _SearchModeHandler, new_text: str) -> None:
    selection_start, selection_end = handler.get_selection_from_widget()
    old_subject = handler.get_widget_text()
    new_subject = (
        old_subject[:selection_start] + new_text + old_subject[selection_end:]
    )
    handler.set_widget_text(new_subject)


def _replace_all(
    api: Api,
    handler: _SearchModeHandler,
    regex: re.Pattern[str],
    new_text: str,
) -> int:
    count = 0
    with api.undo.capture():
        for sub in api.subs.events:
            old_subject_text = handler.get_subject_text(sub)
            new_subject_text = re.sub(regex, new_text, old_subject_text)
            if old_subject_text != new_subject_text:
                handler.set_subject_text(sub, new_subject_text)
                count += len(re.findall(regex, old_subject_text))
        if count:
            api.subs.selected_indexes = []
    return count


def _count(
    api: Api, handler: _SearchModeHandler, regex: re.Pattern[str]
) -> int:
    count = 0
    for sub in api.subs.events:
        subject_text = handler.get_subject_text(sub)
        count += len(re.findall(regex, subject_text))
    return count


class _SearchModeGroupBox(QGroupBox):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Search mode:", parent)
        self._radio_buttons = {
            SearchMode.TEXT: QRadioButton("Text", self),
            SearchMode.NOTE: QRadioButton("Note", self),
            SearchMode.ACTOR: QRadioButton("Actor", self),
            SearchMode.STYLE: QRadioButton("Style", self),
        }
        layout = QVBoxLayout(self)
        for radio_button in self._radio_buttons.values():
            layout.addWidget(radio_button)
        self._radio_buttons[SearchMode.TEXT].setChecked(True)

    def set_value(self, value: SearchMode) -> None:
        self._radio_buttons[value].setChecked(True)

    def get_value(self) -> SearchMode:
        for key, radio_button in self._radio_buttons.items():
            if radio_button.isChecked():
                return key
        raise AssertionError


class _SearchTextEdit(QComboBox):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setMaxCount(MAX_HISTORY_ENTRIES)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        completer = self.completer()
        completer.setCaseSensitivity(Qt.CaseSensitive)
        self.setCompleter(completer)


class _SearchDialog(Dialog):
    def __init__(
        self,
        api: Api,
        main_window: QMainWindow,
        show_replace_controls: bool,
    ) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._api = api

        self.search_text_edit = _SearchTextEdit(self)
        self.replacement_text_edit = QLineEdit(self)
        self.case_chkbox = QCheckBox("Case sensitivity", self)
        self.regex_chkbox = QCheckBox("Use regular expressions", self)
        self.search_mode_group_box = _SearchModeGroupBox(self)

        search_label = QLabel("Text to search for:", self)
        replace_label = QLabel("Text to replace with:", self)

        strip = QDialogButtonBox(self)
        strip.setOrientation(Qt.Vertical)
        self.find_next_btn = strip.addButton("Find next", strip.ActionRole)
        self.find_next_btn.setDefault(True)
        self.find_prev_btn = strip.addButton("Find previous", strip.ActionRole)
        self.count_btn = strip.addButton("Count occurences", strip.ActionRole)
        self.replace_sel_btn = strip.addButton(
            "Replace selection", strip.ActionRole
        )
        self.replace_all_btn = strip.addButton("Replace all", strip.ActionRole)
        strip.addButton("Cancel", strip.RejectRole)
        strip.clicked.connect(self.action)
        strip.rejected.connect(self.reject)

        settings_box = QWidget(self)
        settings_box_layout = QVBoxLayout(settings_box)
        settings_box_layout.setSpacing(16)
        settings_box_layout.setContentsMargins(0, 0, 0, 0)
        for widget in [
            search_label,
            self.search_text_edit,
            replace_label,
            self.replacement_text_edit,
            self.case_chkbox,
            self.regex_chkbox,
            self.search_mode_group_box,
            strip,
        ]:
            settings_box_layout.addWidget(widget)

        if not show_replace_controls:
            replace_label.hide()
            self.replacement_text_edit.hide()
            self.replace_sel_btn.hide()
            self.replace_all_btn.hide()

        layout = QHBoxLayout(self)
        layout.setSpacing(24)
        layout.addWidget(settings_box)
        layout.addWidget(strip)

        if show_replace_controls:
            self.setWindowTitle("Search and replace...")
        else:
            self.setWindowTitle("Search...")

        self._load_opt()
        self._update_replacement_enabled()
        self.search_text_edit.lineEdit().selectAll()

    def reject(self) -> Any:
        self._save_opt()
        return super().reject()

    @async_slot(QAbstractButton)
    async def action(self, sender: QAbstractButton) -> None:
        self._save_opt()
        if sender == self.replace_sel_btn:
            await self._replace_selection()
        elif sender == self.replace_all_btn:
            await self._replace_all()
        elif sender == self.find_prev_btn:
            await self._search(reverse=True)
        elif sender == self.find_next_btn:
            await self._search(reverse=False)
        elif sender == self.count_btn:
            await self._count()

    async def _replace_selection(self) -> None:
        _replace_selection(self._handler, self._target_text)
        self._update_replacement_enabled()

    async def _replace_all(self) -> None:
        self._push_search_history()
        count = _replace_all(
            self._api, self._handler, self._search_regex, self._target_text
        )
        await show_notice(
            f"Replaced {count} occurences."
            if count
            else "No occurences found.",
            self,
        )

    async def _search(self, reverse: bool) -> None:
        self._push_search_history()
        result = _search(self._api, self._handler, self._search_regex, reverse)
        if not result:
            await show_notice("No occurences found.", self)
        self._update_replacement_enabled()

    async def _count(self) -> None:
        self._push_search_history()
        count = _count(self._api, self._handler, self._search_regex)
        await show_notice(
            f"Found {count} occurences." if count else "No occurences found.",
            self,
        )

    def _update_replacement_enabled(self) -> None:
        (
            selection_start,
            selection_end,
        ) = self._handler.get_selection_from_widget()
        self.replace_sel_btn.setEnabled(selection_start != selection_end)

    def _push_search_history(self) -> None:
        text = self._text  # binding it to a variable is important
        idx = self.search_text_edit.findText(text)
        if idx is not None:
            self.search_text_edit.removeItem(idx)
        self.search_text_edit.insertItem(0, text)
        self.search_text_edit.setCurrentIndex(0)

    def _load_opt(self) -> None:
        self.search_text_edit.clear()
        self.search_text_edit.addItems(
            [item for item in self._opt["history"] if item]
        )
        self.case_chkbox.setChecked(self._opt["case_sensitive"])
        self.regex_chkbox.setChecked(self._opt["use_regexes"])
        self.search_mode_group_box.set_value(self._opt["mode"])

    def _save_opt(self) -> None:
        self._opt["history"] = [
            self.search_text_edit.itemText(i)
            for i in range(self.search_text_edit.count())
        ]
        self._opt["use_regexes"] = self._use_regexes
        self._opt["case_sensitive"] = self._case_sensitive
        self._opt["mode"] = int(self._mode)

    @property
    def _opt(self) -> Any:
        return self._api.cfg.opt["search"]

    @property
    def _text(self) -> str:
        return cast(str, self.search_text_edit.currentText())

    @property
    def _target_text(self) -> str:
        return cast(str, self.replacement_text_edit.text())

    @property
    def _use_regexes(self) -> bool:
        return cast(bool, self.regex_chkbox.isChecked())

    @property
    def _case_sensitive(self) -> bool:
        return cast(bool, self.case_chkbox.isChecked())

    @property
    def _mode(self) -> SearchMode:
        return self.search_mode_group_box.get_value()

    @property
    def _handler(self) -> _SearchModeHandler:
        return _HANDLERS[self._mode](self._main_window)

    @property
    def _search_regex(self) -> re.Pattern[str]:
        return _create_search_regex(
            self._text, self._case_sensitive, self._use_regexes
        )


class SearchCommand(BaseCommand):
    names = ["search"]
    help_text = "Opens up the search dialog."

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QMainWindow) -> None:
        dialog = _SearchDialog(
            self.api, main_window, show_replace_controls=False
        )
        await async_dialog_exec(dialog)


class SearchAndReplaceCommand(BaseCommand):
    names = ["search-and-replace"]
    help_text = "Opens up the search and replace dialog."

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QMainWindow) -> None:
        dialog = _SearchDialog(
            self.api, main_window, show_replace_controls=True
        )
        await async_dialog_exec(dialog)


class SearchRepeatCommand(BaseCommand):
    names = ["search-repeat", "search-again"]
    help_text = "Repeats last search operation."

    @property
    def is_enabled(self) -> bool:
        return len(self.api.cfg.opt["search"]["history"]) > 0

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QMainWindow) -> None:
        handler = _HANDLERS[self.api.cfg.opt["search"]["mode"]](main_window)
        result = _search(
            self.api,
            handler,
            _create_search_regex(
                self.api.cfg.opt["search"]["history"][0],
                self.api.cfg.opt["search"]["case_sensitive"],
                self.api.cfg.opt["search"]["use_regexes"],
            ),
            self.args.reverse,
        )
        if not result:
            await show_notice("No occurences found.", main_window)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--above",
            dest="reverse",
            action="store_true",
            help="search forward",
        )
        group.add_argument(
            "--below",
            dest="reverse",
            action="store_false",
            help="search backward",
        )


COMMANDS = [SearchCommand, SearchAndReplaceCommand, SearchRepeatCommand]
