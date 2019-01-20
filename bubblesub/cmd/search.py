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
import re
import traceback
import typing as T

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.ass.event import Event
from bubblesub.opt.general import SearchMode
from bubblesub.ui.util import show_notice

MAX_HISTORY_ENTRIES = 25


def _create_search_regex(
    text: str, case_sensitive: bool, use_regexes: bool
) -> T.Pattern[str]:
    return re.compile(
        text if use_regexes else re.escape(text),
        flags=0 if case_sensitive else re.I,
    )


class _SearchModeHandler(abc.ABC):
    def __init__(self, main_window: QtWidgets.QMainWindow) -> None:
        self.main_window = main_window

    @abc.abstractmethod
    def get_subject_text(self, sub: Event) -> str:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def set_subject_text(self, sub: Event, value: str) -> None:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_subject_widget_name(self) -> str:
        raise NotImplementedError("not implemented")

    def get_subject_widget(self) -> QtWidgets.QWidget:
        widget = self.main_window.findChild(
            QtWidgets.QWidget, self.get_subject_widget_name()
        )
        if isinstance(widget, QtWidgets.QComboBox):
            widget = widget.lineEdit()
        return widget

    def select_text_on_widget(
        self, selection_start: int, selection_end: int
    ) -> None:
        widget = self.get_subject_widget()
        if isinstance(widget, QtWidgets.QPlainTextEdit):
            cursor = widget.textCursor()
            cursor.setPosition(selection_start)
            cursor.setPosition(selection_end, QtGui.QTextCursor.KeepAnchor)
            widget.setTextCursor(cursor)
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.setSelection(
                selection_start, selection_end - selection_start
            )
        else:
            raise AssertionError(f"unknown search widget type ({type(widget)}")
        widget.setFocus()

    def get_selection_from_widget(self) -> T.Tuple[int, int]:
        widget = self.get_subject_widget()
        if isinstance(widget, QtWidgets.QPlainTextEdit):
            cursor = widget.textCursor()
            return (cursor.selectionStart(), cursor.selectionEnd())
        if isinstance(widget, QtWidgets.QLineEdit):
            return (
                widget.selectionStart(),
                widget.selectionStart() + len(widget.selectedText()),
            )
        raise AssertionError(f"unknown search widget type ({type(widget)})")

    def get_widget_text(self) -> str:
        widget = self.get_subject_widget()
        if isinstance(widget, QtWidgets.QPlainTextEdit):
            return T.cast(str, widget.toPlainText())
        if isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()
        raise AssertionError(f"unknown search widget type ({type(widget)})")

    def set_widget_text(self, text: str) -> None:
        widget = self.get_subject_widget()
        if isinstance(widget, QtWidgets.QPlainTextEdit):
            widget.document().setPlainText(text)
        if isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(text)
        else:
            raise AssertionError(
                f"unknown search widget type ({type(widget)})"
            )


class _TextSearchModeHandler(_SearchModeHandler):
    def get_subject_text(self, sub: Event) -> str:
        return sub.text.replace("\\N", "\n")

    def set_subject_text(self, sub: Event, value: str) -> None:
        sub.text = value.replace("\n", "\\N")

    def get_subject_widget_name(self) -> QtWidgets.QWidget:
        return "text-editor"


class _NoteSearchModeHandler(_SearchModeHandler):
    def get_subject_text(self, sub: Event) -> str:
        return sub.note.replace("\\N", "\n")

    def set_subject_text(self, sub: Event, value: str) -> None:
        sub.note = value.replace("\n", "\\N")

    def get_subject_widget_name(self) -> QtWidgets.QWidget:
        return "note-editor"


class _ActorSearchModeHandler(_SearchModeHandler):
    def get_subject_text(self, sub: Event) -> str:
        return sub.actor

    def set_subject_text(self, sub: Event, value: str) -> None:
        sub.actor = value

    def get_subject_widget_name(self) -> QtWidgets.QWidget:
        return "actor-editor"


class _StyleSearchModeHandler(_SearchModeHandler):
    def get_subject_text(self, sub: Event) -> str:
        return sub.style

    def set_subject_text(self, sub: Event, value: str) -> None:
        sub.style = value

    def get_subject_widget_name(self) -> QtWidgets.QWidget:
        return "style-editor"


_HANDLERS: T.Dict[SearchMode, T.Type[_SearchModeHandler]] = {
    SearchMode.Text: _TextSearchModeHandler,
    SearchMode.Note: _NoteSearchModeHandler,
    SearchMode.Actor: _ActorSearchModeHandler,
    SearchMode.Style: _StyleSearchModeHandler,
}


def _narrow_match(
    handler: _SearchModeHandler,
    matches: T.List[T.Match[str]],
    idx: int,
    selected_idx: T.Optional[int],
    reverse: bool,
) -> T.Optional[T.Match[str]]:
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
    api: Api, handler: _SearchModeHandler, regex: T.Pattern[str], reverse: bool
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
    api: Api, handler: _SearchModeHandler, regex: T.Pattern[str], new_text: str
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
    api: Api, handler: _SearchModeHandler, regex: T.Pattern[str]
) -> int:
    count = 0
    for sub in api.subs.events:
        subject_text = handler.get_subject_text(sub)
        count += len(re.findall(regex, subject_text))
    return count


class _SearchModeGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__("Search mode:", parent)
        self._radio_buttons = {
            SearchMode.Text: QtWidgets.QRadioButton("Text", self),
            SearchMode.Note: QtWidgets.QRadioButton("Note", self),
            SearchMode.Actor: QtWidgets.QRadioButton("Actor", self),
            SearchMode.Style: QtWidgets.QRadioButton("Style", self),
        }
        layout = QtWidgets.QVBoxLayout(self)
        for radio_button in self._radio_buttons.values():
            layout.addWidget(radio_button)
        self._radio_buttons[SearchMode.Text].setChecked(True)

    def set_value(self, value: SearchMode) -> None:
        self._radio_buttons[value].setChecked(True)

    def get_value(self) -> SearchMode:
        for key, radio_button in self._radio_buttons.items():
            if radio_button.isChecked():
                return key
        raise AssertionError


class _SearchTextEdit(QtWidgets.QComboBox):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setMaxCount(MAX_HISTORY_ENTRIES)
        self.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        completer = self.completer()
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.setCompleter(completer)


class _SearchDialog(QtWidgets.QDialog):
    def __init__(
        self,
        api: Api,
        main_window: QtWidgets.QMainWindow,
        show_replace_controls: bool,
        parent: QtWidgets.QWidget = None,
    ) -> None:
        super().__init__(parent)
        self._main_window = main_window
        self._api = api

        self.search_text_edit = _SearchTextEdit(self)
        self.replacement_text_edit = QtWidgets.QLineEdit(self)
        self.case_chkbox = QtWidgets.QCheckBox("Case sensitivity", self)
        self.regex_chkbox = QtWidgets.QCheckBox(
            "Use regular expressions", self
        )
        self.search_mode_group_box = _SearchModeGroupBox(self)

        search_label = QtWidgets.QLabel("Text to search for:", self)
        replace_label = QtWidgets.QLabel("Text to replace with:", self)

        strip = QtWidgets.QDialogButtonBox(self)
        strip.setOrientation(QtCore.Qt.Vertical)
        self.find_next_btn = strip.addButton("Find next", strip.ActionRole)
        self.find_prev_btn = strip.addButton("Find previous", strip.ActionRole)
        self.count_btn = strip.addButton("Count occurences", strip.ActionRole)
        self.replace_sel_btn = strip.addButton(
            "Replace selection", strip.ActionRole
        )
        self.replace_all_btn = strip.addButton("Replace all", strip.ActionRole)
        strip.addButton("Cancel", strip.RejectRole)
        strip.clicked.connect(self.action)
        strip.rejected.connect(self.reject)

        settings_box = QtWidgets.QWidget(self)
        settings_box_layout = QtWidgets.QVBoxLayout(settings_box)
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

        layout = QtWidgets.QHBoxLayout(self)
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

    def reject(self) -> T.Any:
        self._save_opt()
        return super().reject()

    def action(self, sender: QtWidgets.QAbstractButton) -> None:
        try:
            self._save_opt()
            if sender == self.replace_sel_btn:
                self._replace_selection()
            elif sender == self.replace_all_btn:
                self._replace_all()
            elif sender == self.find_prev_btn:
                self._search(reverse=True)
            elif sender == self.find_next_btn:
                self._search(reverse=False)
            elif sender == self.count_btn:
                self._count()
        except Exception as ex:  # pylint: disable=broad-except
            self._api.log.error(str(ex))
            traceback.print_exc()

    def _replace_selection(self) -> None:
        _replace_selection(self._handler, self._target_text)
        self._update_replacement_enabled()

    def _replace_all(self) -> None:
        self._push_search_history()
        count = _replace_all(
            self._api, self._handler, self._search_regex, self._target_text
        )
        show_notice(
            f"Replaced {count} occurences."
            if count
            else "No occurences found."
        )

    def _search(self, reverse: bool) -> None:
        self._push_search_history()
        result = _search(self._api, self._handler, self._search_regex, reverse)
        if not result:
            show_notice("No occurences found.")
        self._update_replacement_enabled()

    def _count(self) -> None:
        self._push_search_history()
        count = _count(self._api, self._handler, self._search_regex)
        show_notice(
            f"Found {count} occurences." if count else "No occurences found."
        )

    def _update_replacement_enabled(self) -> None:
        selection_start, selection_end = (
            self._handler.get_selection_from_widget()
        )
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
            [item for item in self._opt.history if item]
        )
        self.case_chkbox.setChecked(self._opt.case_sensitive)
        self.regex_chkbox.setChecked(self._opt.use_regexes)
        self.search_mode_group_box.set_value(self._opt.mode)

    def _save_opt(self) -> None:
        self._opt.history = [
            self.search_text_edit.itemText(i)
            for i in range(self.search_text_edit.count())
        ]
        self._opt.use_regexes = self._use_regexes
        self._opt.case_sensitive = self._case_sensitive
        self._opt.mode = self._mode

    @property
    def _opt(self) -> T.Any:
        return self._api.opt.general.search

    @property
    def _text(self) -> str:
        return T.cast(str, self.search_text_edit.currentText())

    @property
    def _target_text(self) -> str:
        return T.cast(str, self.replacement_text_edit.text())

    @property
    def _use_regexes(self) -> bool:
        return T.cast(bool, self.regex_chkbox.isChecked())

    @property
    def _case_sensitive(self) -> bool:
        return T.cast(bool, self.case_chkbox.isChecked())

    @property
    def _mode(self) -> SearchMode:
        return self.search_mode_group_box.get_value()

    @property
    def _handler(self) -> _SearchModeHandler:
        return _HANDLERS[self._mode](self._main_window)

    @property
    def _search_regex(self) -> T.Pattern[str]:
        return _create_search_regex(
            self._text, self._case_sensitive, self._use_regexes
        )


class SearchCommand(BaseCommand):
    names = ["search"]
    help_text = "Opens up the search dialog."

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        _SearchDialog(
            self.api, main_window, show_replace_controls=False
        ).exec_()


class SearchAndReplaceCommand(BaseCommand):
    names = ["search-and-replace"]
    help_text = "Opens up the search and replace dialog."

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        _SearchDialog(
            self.api, main_window, show_replace_controls=True
        ).exec_()


class SearchRepeatCommand(BaseCommand):
    names = ["search-repeat", "search-again"]
    help_text = "Repeats last search operation."

    @property
    def is_enabled(self) -> bool:
        return len(self.api.opt.general.search.history) > 0

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        handler = _HANDLERS[self.api.opt.general.search.mode](main_window)
        result = _search(
            self.api,
            handler,
            _create_search_regex(
                self.api.opt.general.search.history[0],
                self.api.opt.general.search.case_sensitive,
                self.api.opt.general.search.use_regexes,
            ),
            self.args.reverse,
        )
        if not result:
            show_notice("No occurences found.")

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
