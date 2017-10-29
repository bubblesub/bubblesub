import bubblesub.util
import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand
from enchant import Dict
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


def _match_words(api):
    import regex
    for sub in api.subs.selected_lines:
        text = regex.sub(
            r'\\[Nnh]',
            '  ',  # two spaces so that matches mantain position in text
            sub.text)
        for match in regex.finditer(r'\p{L}[\p{L}\p{P}]*\p{L}|\p{L}', text):
            yield (sub.id, match)


class SpellCheckDialog(QtWidgets.QDialog):
    def __init__(self, api, main_window, word_matches):
        super().__init__(main_window)
        self._main_window = main_window
        self._api = api
        self._word_matches = list(word_matches)
        self._dict = Dict('en_US')

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
        self._dict.add(self._mispelt_text_edit.text())
        self._next()

    def _ignore(self):
        self._next()

    def _ignore_all(self):
        self._dict.add_to_session(self._mispelt_text_edit.text())
        self._next()

    def _next(self):
        idx, match = self._iter_to_next_mispelt_match()
        if match:
            self._focus_match(idx, match)
            return True
        bubblesub.ui.util.notice('No more results.')
        self.reject()
        return False

    def _iter_to_next_mispelt_match(self):
        while len(self._word_matches):
            idx, match = self._word_matches.pop(0)
            if not self._dict.check(match.group(0)):
                return idx, match
        return None, None

    def _focus_match(self, idx, match):
        self._api.subs.selected_indexes = [idx]

        cursor = self._main_window.editor.center.text_edit.textCursor()
        cursor.setPosition(match.start())
        cursor.setPosition(match.end(), QtGui.QTextCursor.KeepAnchor)
        self._main_window.editor.center.text_edit.setTextCursor(cursor)

        self._mispelt_text_edit.setText(match.group(0))

        self._suggestions_list_view.model().clear()
        for suggestion in self._dict.suggest(match.group(0)):
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
        word_matches = _match_words(self.api)

        async def run(api, main_window):
            SpellCheckDialog(api, main_window, word_matches)

        await self.api.gui.exec(run)
