import re
import bubblesub.ui.util
from bubblesub.cmd.registry import BaseCommand
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


MAX_HISTORY_ENTRIES = 25


def _search(api, text, case_sensitive, use_regexes, direction):
    num_lines = len(api.subs.lines)
    if not api.subs.has_selection:
        sub_idx = None
        iterator = range(num_lines)
        if direction < 0:
            iterator = reversed(iterator)
    else:
        sub_idx = api.subs.selected_indexes[0]
        iterator = list(
            (sub_idx + direction * i) % num_lines
            for i in range(num_lines)
        )

    regex = re.compile(
        text if use_regexes else re.escape(text),
        flags=(0 if case_sensitive else re.I))

    for idx in iterator:
        matches = list(re.finditer(regex, api.subs.lines[idx].text))
        if not matches:
            continue

        sel_match = None
        if idx == sub_idx:
            cursor = api.gui.main_window.editor.text_edit.textCursor()
            if cursor.selectionEnd() == cursor.selectionStart():
                if direction > 0:
                    sel_match = matches[0]
            elif direction > 0:
                for match in matches:
                    if match.end() > cursor.selectionEnd():
                        sel_match = match
                        break
            elif direction < 0:
                for match in reversed(matches):
                    if match.start() < cursor.selectionStart():
                        sel_match = match
                        break
        elif direction > 0:
            sel_match = matches[0]
        elif direction < 0:
            sel_match = matches[-1]

        if not sel_match:
            continue

        api.subs.selected_indexes = [idx]
        cursor = api.gui.main_window.editor.text_edit.textCursor()
        cursor.setPosition(sel_match.start())
        cursor.setPosition(sel_match.end(), QtGui.QTextCursor.KeepAnchor)
        api.gui.main_window.editor.text_edit.setTextCursor(cursor)
        return True

    bubblesub.ui.util.notice('No occurrences found.')
    return False


def _replace_selection(api, new_text):
    edit = api.gui.main_window.editor.text_edit
    text = edit.toPlainText()
    text = (
        text[:edit.textCursor().selectionStart()] +
        new_text +
        text[edit.textCursor().selectionEnd():])
    edit.document().setPlainText(text)


class SearchDialog(QtWidgets.QDialog):
    def __init__(self, api, show_replace_controls, parent=None):
        super().__init__(parent)
        self._api = api

        self.search_text_edit = QtWidgets.QComboBox(
            self,
            editable=True,
            maxCount=MAX_HISTORY_ENTRIES,
            sizePolicy=QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Preferred),
            insertPolicy=QtWidgets.QComboBox.InsertAtTop)
        self.replacement_text_edit = QtWidgets.QLineEdit(self)
        self.case_chkbox = QtWidgets.QCheckBox('Case sensitivity', self)
        self.regex_chkbox = QtWidgets.QCheckBox(
            'Use regular expressions', self)

        search_label = QtWidgets.QLabel('Text to search for:', self)
        replace_label = QtWidgets.QLabel('Text to replace with:', self)

        strip = QtWidgets.QDialogButtonBox(
            self, orientation=QtCore.Qt.Vertical)
        self.find_next_btn = strip.addButton('Find next', strip.ActionRole)
        self.find_prev_btn = strip.addButton('Find previous', strip.ActionRole)
        self.replace_btn = strip.addButton(
            'Replace selection', strip.ActionRole)
        strip.addButton('Cancel', strip.RejectRole)
        strip.clicked.connect(self.action)
        strip.rejected.connect(self.reject)

        self._load_opt()
        self._update_replacement_enabled()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(search_label)
        layout.addWidget(self.search_text_edit)
        layout.addWidget(replace_label)
        layout.addWidget(self.replacement_text_edit)
        layout.addWidget(self.case_chkbox)
        layout.addWidget(self.regex_chkbox)
        layout.addWidget(strip)
        settings_box = QtWidgets.QWidget(self)
        settings_box.setLayout(layout)

        if not show_replace_controls:
            replace_label.hide()
            self.replacement_text_edit.hide()
            self.replace_btn.hide()

        layout = QtWidgets.QHBoxLayout(self, spacing=24)
        layout.addWidget(settings_box)
        layout.addWidget(strip)
        self.setLayout(layout)

    def reject(self, *args):
        self._save_opt()
        return super().reject(*args)

    def action(self, sender):
        self._save_opt()
        if sender == self.replace_btn:
            self._replace()
        elif sender == self.find_prev_btn:
            self._search(-1)
        elif sender == self.find_next_btn:
            self._search(1)

    def _update_replacement_enabled(self):
        cursor = self._api.gui.main_window.editor.text_edit.textCursor()
        self.replace_btn.setEnabled(cursor.selectedText() != '')

    def _replace(self):
        _replace_selection(self._api, self.replacement_text_edit.text())
        self._update_replacement_enabled()

    def _search(self, direction):
        _search(
            self._api,
            self.search_text_edit.currentText(),
            self.case_chkbox.isChecked(),
            self.regex_chkbox.isChecked(),
            direction)
        self._update_replacement_enabled()

    def _load_opt(self):
        self.search_text_edit.clear()
        self.search_text_edit.addItems(
            [item for item in self._opt['history'] if item])
        self.case_chkbox.setChecked(self._opt['case_sensitive'])
        self.regex_chkbox.setChecked(self._opt['use_regexes'])

    def _save_opt(self):
        self._opt['history'] = [
            self.search_text_edit.itemText(i)
            for i in range(self.search_text_edit.count())]
        self._opt['use_regexes'] = self.regex_chkbox.isChecked()
        self._opt['case_sensitive'] = self.case_chkbox.isChecked()

    @property
    def _opt(self):
        return self._api.opt.general['search']


class SearchCommand(BaseCommand):
    name = 'edit/search'

    def run(self, api):
        dialog = SearchDialog(api, show_replace_controls=False)
        dialog.exec_()


class SearchAndReplaceCommand(BaseCommand):
    name = 'edit/search-and-replace'

    def run(self, api):
        dialog = SearchDialog(api, show_replace_controls=True)
        dialog.exec_()


class SearchRepeatCommand(BaseCommand):
    name = 'edit/search-repeat'

    def enabled(self, api):
        return len(api.opt.general['search']['history']) > 0

    def run(self, api, direction):
        opt = api.opt.general['search']
        _search(
            api,
            opt['history'][0],
            opt['case_sensitive'],
            opt['use_regexes'],
            direction)
