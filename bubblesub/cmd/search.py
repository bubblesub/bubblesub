import re
import bubblesub.ui.util
from bubblesub.cmd.registry import BaseCommand
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


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
        match = list(re.finditer(regex, api.subs.lines[idx].text))
        if not match:
            continue

        sel_match = None
        if idx == sub_idx:
            cursor = api.gui.main_window.editor.text_edit.textCursor()
            if cursor.selectionEnd() == cursor.selectionStart():
                if direction > 0:
                    sel_match = match[0]
            elif direction > 0:
                for m in match:
                    if m.end() > cursor.selectionEnd():
                        sel_match = m
                        break
            elif direction < 0:
                for m in reversed(match):
                    if m.start() < cursor.selectionStart():
                        sel_match = m
                        break
        elif direction > 0:
            sel_match = match[0]
        elif direction < 0:
            sel_match = match[-1]

        if not sel_match:
            continue

        api.subs.selected_indexes = [idx]
        cursor = api.gui.main_window.editor.text_edit.textCursor()
        cursor.setPosition(sel_match.start())
        cursor.setPosition(sel_match.end(), QtGui.QTextCursor.KeepAnchor)
        api.gui.main_window.editor.text_edit.setTextCursor(cursor)
        return True

    return False


class SearchDialog(QtWidgets.QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self._api = api

        self.text_edit = QtWidgets.QLineEdit()
        self.case_chkbox = QtWidgets.QCheckBox('Case sensitivity')
        self.regex_chkbox = QtWidgets.QCheckBox('Use regular expressions')

        label = QtWidgets.QLabel('Text to search for:')
        strip = QtWidgets.QDialogButtonBox(
            self, orientation=QtCore.Qt.Vertical)
        self.find_next_btn = strip.addButton('Find next', strip.ActionRole)
        self.find_prev_btn = strip.addButton('Find previous', strip.ActionRole)
        strip.addButton('Cancel', strip.RejectRole)
        strip.clicked.connect(self.action)
        strip.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.case_chkbox)
        layout.addWidget(self.regex_chkbox)
        layout.addWidget(strip)
        settings_box = QtWidgets.QWidget()
        settings_box.setLayout(layout)

        layout = QtWidgets.QHBoxLayout(spacing=24)
        layout.addWidget(settings_box)
        layout.addWidget(strip)
        self.setLayout(layout)

    def action(self, sender):
        if sender == self.find_prev_btn:
            direction = -1
        elif sender == self.find_next_btn:
            direction = 1
        else:
            direction = 0
        if direction:
            result = _search(
                self._api,
                self.text_edit.text(),
                self.case_chkbox.isChecked(),
                self.regex_chkbox.isChecked(),
                direction)
            if not result:
                bubblesub.ui.util.notice('No occurrences found.')


class SearchCommand(BaseCommand):
    name = 'edit/search'

    def __init__(self):
        self.dialog = None

    def run(self, api):
        if not self.dialog:
            self.dialog = SearchDialog(api)
        self.dialog.exec_()
