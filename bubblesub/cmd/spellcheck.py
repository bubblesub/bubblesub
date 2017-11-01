import bubblesub.util
import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand
from enchant import Dict
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


class SpellCheckDialog(QtWidgets.QDialog):
    def __init__(self, api, main_window, dictionary):
        super().__init__(main_window)
        self._main_window = main_window
        self._api = api
        self._dictionary = dictionary
        self._lines_to_spellcheck = api.subs.selected_lines

        self._mispelt_text_edit = QtWidgets.QLineEdit(self, readOnly=True)
        self._replacement_text_edit = QtWidgets.QLineEdit(self)
        self._suggestions_list_view = QtWidgets.QListView(self)
        self._suggestions_list_view.setModel(QtGui.QStandardItemModel())
        self._suggestions_list_view.clicked.connect(self._on_suggestion_click)

        box = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel('Mispelt word:', self))
        layout.addWidget(self._mispelt_text_edit)
        layout.addWidget(QtWidgets.QLabel('Replacement:', self))
        layout.addWidget(self._replacement_text_edit)
        layout.addWidget(QtWidgets.QLabel('Suggestions:', self))
        layout.addWidget(self._suggestions_list_view)

        strip = QtWidgets.QDialogButtonBox(
            self, orientation=QtCore.Qt.Vertical)
        self.add_btn = strip.addButton('Add to dictionary', strip.ActionRole)
        self.ignore_btn = strip.addButton('Ignore', strip.ActionRole)
        self.ignore_all_btn = strip.addButton('Ignore all', strip.ActionRole)
        self.replace_btn = strip.addButton('Replace', strip.ActionRole)
        strip.addButton('Cancel', strip.RejectRole)
        strip.clicked.connect(self.action)
        strip.rejected.connect(self.reject)

        layout = QtWidgets.QHBoxLayout(self, spacing=24)
        layout.addWidget(box)
        layout.addWidget(strip)

        if self._next():
            self.exec_()

    def action(self, sender):
        if sender == self.replace_btn:
            self._replace()
        elif sender == self.add_btn:
            self._add_to_dictionary()
        elif sender == self.ignore_btn:
            self._ignore()
        elif sender == self.ignore_all_btn:
            self._ignore_all()

    def _replace(self):
        edit = self._main_window.editor.center.text_edit
        text = edit.toPlainText()
        text = (
            text[:edit.textCursor().selectionStart()] +
            self._replacement_text_edit.text() +
            text[edit.textCursor().selectionEnd():])
        edit.document().setPlainText(text)
        self._next()

    def _add_to_dictionary(self):
        self._dictionary.add(self._mispelt_text_edit.text())
        self._next()

    def _ignore(self):
        self._next()

    def _ignore_all(self):
        self._dictionary.add_to_session(self._mispelt_text_edit.text())
        self._next()

    def _next(self):
        idx, start, end = self._iter_to_next_mispelt_match()
        if idx is not None:
            self._focus_match(idx, start, end)
            return True
        bubblesub.ui.util.notice('No more results.')
        self.reject()
        return False

    def _iter_to_next_mispelt_match(self):
        cursor = self._main_window.editor.center.text_edit.textCursor()
        while self._lines_to_spellcheck:
            line = self._lines_to_spellcheck[0]
            for start, end in bubblesub.util.spell_check_ass_line(
                    self._dictionary, line.text):
                if len(self._api.subs.selected_indexes) > 1 \
                or line.id > self._api.subs.selected_indexes[0] \
                or start > cursor.selectionStart() \
                or cursor.selectionStart() == cursor.selectionEnd():
                    return line.id, start, end
            self._lines_to_spellcheck.pop(0)
        return None, None, None

    def _focus_match(self, idx, start, end):
        self._api.subs.selected_indexes = [idx]
        mispelt_word = self._api.subs.lines[idx].text[start:end]

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

    def _on_suggestion_click(self, event):
        self._replacement_text_edit.setText(event.data())


class EditSpellCheckCommand(CoreCommand):
    name = 'edit/spell-check'
    menu_name = 'Spell check...'

    @property
    def is_enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        if not self.api.opt.general['spell_check']:
            bubblesub.ui.util.error('Spell check was disabled in config.')

        dictionary = Dict(self.api.opt.general['spell_check'])

        async def run(api, main_window):
            SpellCheckDialog(api, main_window, dictionary)

        await self.api.gui.exec(run)
