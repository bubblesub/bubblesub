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

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.ass.util import spell_check_ass_line
from bubblesub.spell_check import SpellChecker, SpellCheckerError
from bubblesub.ui.util import (
    Dialog,
    async_dialog_exec,
    async_slot,
    show_error,
    show_notice,
)
from bubblesub.util import ucfirst


class _SpellCheckDialog(Dialog):
    def __init__(
        self,
        api: Api,
        main_window: QtWidgets.QMainWindow,
        spell_checker: SpellChecker,
    ) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._api = api
        self._spell_checker = spell_checker
        self._lines_to_spellcheck = api.subs.selected_events

        self._mispelt_text_edit = QtWidgets.QLineEdit(self)
        self._mispelt_text_edit.setReadOnly(True)
        self._replacement_text_edit = QtWidgets.QLineEdit(self)
        self._suggestions_list_view = QtWidgets.QListView(self)
        self._suggestions_list_view.setModel(QtGui.QStandardItemModel())
        self._suggestions_list_view.clicked.connect(self._on_suggestion_click)

        box = QtWidgets.QWidget(self)
        box_layout = QtWidgets.QVBoxLayout(box)
        box_layout.setContentsMargins(0, 0, 0, 0)
        box_layout.addWidget(QtWidgets.QLabel("Mispelt word:", self))
        box_layout.addWidget(self._mispelt_text_edit)
        box_layout.addWidget(QtWidgets.QLabel("Replacement:", self))
        box_layout.addWidget(self._replacement_text_edit)
        box_layout.addWidget(QtWidgets.QLabel("Suggestions:", self))
        box_layout.addWidget(self._suggestions_list_view)

        strip = QtWidgets.QDialogButtonBox(self)
        strip.setOrientation(QtCore.Qt.Vertical)
        self.add_btn = strip.addButton("Add to dictionary", strip.ActionRole)
        self.ignore_btn = strip.addButton("Ignore", strip.ActionRole)
        self.ignore_all_btn = strip.addButton("Ignore all", strip.ActionRole)
        self.replace_btn = strip.addButton("Replace", strip.ActionRole)
        strip.addButton("Cancel", strip.RejectRole)
        strip.clicked.connect(self.action)
        strip.rejected.connect(self.reject)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(24)
        layout.addWidget(box)
        layout.addWidget(strip)

        self.setWindowTitle("Spell checker")

    @async_slot(QtWidgets.QAbstractButton)
    async def action(self, sender: QtWidgets.QAbstractButton) -> None:
        if sender == self.replace_btn:
            await self._replace()
        elif sender == self.add_btn:
            await self._add_to_dictionary()
        elif sender == self.ignore_btn:
            await self._ignore()
        elif sender == self.ignore_all_btn:
            await self._ignore_all()

    @property
    def text_edit(self) -> QtWidgets.QWidget:
        return self._main_window.findChild(QtWidgets.QWidget, "text-editor")

    async def _replace(self) -> None:
        text = self.text_edit.toPlainText()
        text = (
            text[: self.text_edit.textCursor().selectionStart()]
            + self._replacement_text_edit.text()
            + text[self.text_edit.textCursor().selectionEnd() :]
        )
        self.text_edit.document().setPlainText(text)
        await self.next()

    async def _add_to_dictionary(self) -> None:
        self._spell_checker.add(self._mispelt_text_edit.text())
        await self.next()

    async def _ignore(self) -> None:
        await self.next()

    async def _ignore_all(self) -> None:
        self._spell_checker.add_to_session(self._mispelt_text_edit.text())
        await self.next()

    async def next(self) -> bool:
        ret = self._iter_to_next_mispelt_match()
        if ret is None:
            await show_notice("No more results.", self)
            self.reject()
            return False
        idx, start, end, word = ret
        self._focus_match(idx, start, end, word)
        return True

    def _iter_to_next_mispelt_match(
        self
    ) -> T.Optional[T.Tuple[int, int, int, str]]:
        cursor = self.text_edit.textCursor()
        while self._lines_to_spellcheck:
            line = self._lines_to_spellcheck[0]
            for start, end, word in spell_check_ass_line(
                self._spell_checker, line.text.replace("\\N", "\n")
            ):
                assert line.index is not None
                if (
                    len(self._api.subs.selected_indexes) > 1
                    or line.index > self._api.subs.selected_indexes[0]
                    or start > cursor.selectionStart()
                    or cursor.selectionStart() == cursor.selectionEnd()
                ):
                    return line.index, start, end, word
            self._lines_to_spellcheck.pop(0)
        return None

    def _focus_match(
        self, idx: int, start: int, end: int, mispelt_word: str
    ) -> None:
        self._api.subs.selected_indexes = [idx]

        cursor = self.text_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QtGui.QTextCursor.KeepAnchor)
        self.text_edit.setTextCursor(cursor)

        self._mispelt_text_edit.setText(mispelt_word)

        self._suggestions_list_view.model().clear()
        for suggestion in self._spell_checker.suggest(mispelt_word):
            item = QtGui.QStandardItem(suggestion)
            item.setEditable(False)
            self._suggestions_list_view.model().appendRow(item)

    def _on_suggestion_click(self, event: QtCore.QEvent) -> None:
        self._replacement_text_edit.setText(event.data())


class SpellCheckCommand(BaseCommand):
    names = ["spell-check"]
    help_text = "Opens up the spell check dialog."

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        spell_check_lang = self.api.cfg.opt["gui"]["spell_check"]
        if not spell_check_lang:
            await show_error(
                "Spell check was disabled in config.", main_window
            )
            return

        try:
            dictionary = SpellChecker(spell_check_lang)
        except SpellCheckerError as ex:
            await show_error(ucfirst(str(ex)) + ".", main_window)
            return

        dialog = _SpellCheckDialog(self.api, main_window, dictionary)
        if await dialog.next():
            await async_dialog_exec(dialog)


COMMANDS = [SpellCheckCommand]
