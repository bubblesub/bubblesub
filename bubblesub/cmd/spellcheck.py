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

"""Spell check command."""

import typing as T

import enchant
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ass.util
import bubblesub.ui.util
import bubblesub.util
from bubblesub.api.cmd import BaseCommand


class _SpellCheckDialog(QtWidgets.QDialog):
    def __init__(
            self,
            api: bubblesub.api.Api,
            main_window: QtWidgets.QMainWindow,
            dictionary: enchant.Dict
    ) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._api = api
        self._dictionary = dictionary
        self._lines_to_spellcheck = api.subs.selected_lines

        self._mispelt_text_edit = QtWidgets.QLineEdit(self)
        self._mispelt_text_edit.setReadOnly(True)
        self._replacement_text_edit = QtWidgets.QLineEdit(self)
        self._suggestions_list_view = QtWidgets.QListView(self)
        self._suggestions_list_view.setModel(QtGui.QStandardItemModel())
        self._suggestions_list_view.clicked.connect(self._on_suggestion_click)

        box = QtWidgets.QWidget(self)
        box_layout = QtWidgets.QVBoxLayout(box)
        box_layout.setContentsMargins(0, 0, 0, 0)
        box_layout.addWidget(QtWidgets.QLabel('Mispelt word:', self))
        box_layout.addWidget(self._mispelt_text_edit)
        box_layout.addWidget(QtWidgets.QLabel('Replacement:', self))
        box_layout.addWidget(self._replacement_text_edit)
        box_layout.addWidget(QtWidgets.QLabel('Suggestions:', self))
        box_layout.addWidget(self._suggestions_list_view)

        strip = QtWidgets.QDialogButtonBox(self)
        strip.setOrientation(QtCore.Qt.Vertical)
        self.add_btn = strip.addButton('Add to dictionary', strip.ActionRole)
        self.ignore_btn = strip.addButton('Ignore', strip.ActionRole)
        self.ignore_all_btn = strip.addButton('Ignore all', strip.ActionRole)
        self.replace_btn = strip.addButton('Replace', strip.ActionRole)
        strip.addButton('Cancel', strip.RejectRole)
        strip.clicked.connect(self.action)
        strip.rejected.connect(self.reject)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(24)
        layout.addWidget(box)
        layout.addWidget(strip)

        if self._next():
            self.exec_()

    def action(self, sender: QtWidgets.QWidget) -> None:
        if sender == self.replace_btn:
            self._replace()
        elif sender == self.add_btn:
            self._add_to_dictionary()
        elif sender == self.ignore_btn:
            self._ignore()
        elif sender == self.ignore_all_btn:
            self._ignore_all()

    def _replace(self) -> None:
        edit = self._main_window.editor.center.text_edit
        text = edit.toPlainText()
        text = (
            text[:edit.textCursor().selectionStart()] +
            self._replacement_text_edit.text() +
            text[edit.textCursor().selectionEnd():]
        )
        edit.document().setPlainText(text)
        self._next()

    def _add_to_dictionary(self) -> None:
        self._dictionary.add(self._mispelt_text_edit.text())
        self._next()

    def _ignore(self) -> None:
        self._next()

    def _ignore_all(self) -> None:
        self._dictionary.add_to_session(self._mispelt_text_edit.text())
        self._next()

    def _next(self) -> bool:
        ret = self._iter_to_next_mispelt_match()
        if ret is None:
            bubblesub.ui.util.notice('No more results.')
            self.reject()
            return False
        idx, start, end, word = ret
        self._focus_match(idx, start, end, word)
        return True

    def _iter_to_next_mispelt_match(
            self
    ) -> T.Optional[T.Tuple[int, int, int, str]]:
        cursor = self._main_window.editor.center.text_edit.textCursor()
        while self._lines_to_spellcheck:
            line = self._lines_to_spellcheck[0]
            for start, end, word in bubblesub.ass.util.spell_check_ass_line(
                    self._dictionary, line.text.replace('\\N', '\n')
            ):
                assert line.index is not None
                if len(self._api.subs.selected_indexes) > 1 \
                        or line.index > self._api.subs.selected_indexes[0] \
                        or start > cursor.selectionStart() \
                        or cursor.selectionStart() == cursor.selectionEnd():
                    return line.index, start, end, word
            self._lines_to_spellcheck.pop(0)
        return None

    def _focus_match(
            self,
            idx: int,
            start: int,
            end: int,
            mispelt_word: str
    ) -> None:
        self._api.subs.selected_indexes = [idx]

        cursor = self._main_window.editor.center.text_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QtGui.QTextCursor.KeepAnchor)
        self._main_window.editor.center.text_edit.setTextCursor(cursor)

        self._mispelt_text_edit.setText(mispelt_word)

        self._suggestions_list_view.model().clear()
        for suggestion in self._dictionary.suggest(mispelt_word):
            item = QtGui.QStandardItem(suggestion)
            item.setEditable(False)
            self._suggestions_list_view.model().appendRow(item)

    def _on_suggestion_click(self, event: QtCore.QEvent) -> None:
        self._replacement_text_edit.setText(event.data())


class SpellCheckCommand(BaseCommand):
    """Opens up the spell check dialog."""

    name = 'edit/spell-check'
    menu_name = '&Spell check...'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        spell_check_lang = self.api.opt.general.spell_check
        if not spell_check_lang:
            bubblesub.ui.util.error('Spell check was disabled in config.')
            return

        try:
            dictionary = enchant.Dict(spell_check_lang)
        except enchant.errors.DictNotFoundError:
            bubblesub.ui.util.error(
                f'Spell check language {spell_check_lang} was not found.'
            )
            return

        async def run(
                api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> None:
            _SpellCheckDialog(api, main_window, dictionary)

        await self.api.gui.exec(run)


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    cmd_api.register_core_command(SpellCheckCommand)
