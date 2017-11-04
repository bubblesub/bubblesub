import re
import enum
import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


MAX_HISTORY_ENTRIES = 25


class SearchMode(enum.IntEnum):
    Text = 1
    Note = 2
    Actor = 3
    Style = 4


def _create_search_regex(text, case_sensitive, use_regexes):
    return re.compile(
        text if use_regexes else re.escape(text),
        flags=(0 if case_sensitive else re.I))


def _get_subject_text_by_mode(sub, mode):
    if mode == SearchMode.Text:
        return sub.text
    elif mode == SearchMode.Note:
        return sub.note
    elif mode == SearchMode.Actor:
        return sub.actor
    elif mode == SearchMode.Style:
        return sub.style
    else:
        assert False, 'Invalid mode'


def _set_subject_text_by_mode(sub, mode, value):
    if mode == SearchMode.Text:
        sub.text = value
    elif mode == SearchMode.Note:
        sub.note = value
    elif mode == SearchMode.Actor:
        sub.actor = value
    elif mode == SearchMode.Style:
        sub.style = value
    else:
        assert False, 'Invalid mode'


def _get_subject_widget_by_mode(main_window, mode):
    if mode == SearchMode.Text:
        return main_window.editor.center.text_edit
    elif mode == SearchMode.Note:
        return main_window.editor.center.note_edit
    elif mode == SearchMode.Actor:
        return main_window.editor.bottom_bar.actor_edit.lineEdit()
    elif mode == SearchMode.Style:
        return main_window.editor.bottom_bar.style_edit.lineEdit()


def _select_text_on_widget(widget, selection_start, selection_end):
    if isinstance(widget, QtWidgets.QPlainTextEdit):
        cursor = widget.textCursor()
        cursor.setPosition(selection_start)
        cursor.setPosition(selection_end, QtGui.QTextCursor.KeepAnchor)
        widget.setTextCursor(cursor)
    elif isinstance(widget, QtWidgets.QLineEdit):
        widget.setSelection(selection_start, selection_end - selection_start)
    else:
        assert False, 'Unknown widget type'
    widget.setFocus()


def _get_selection_from_widget(widget):
    if isinstance(widget, QtWidgets.QPlainTextEdit):
        cursor = widget.textCursor()
        return (cursor.selectionStart(), cursor.selectionEnd())
    elif isinstance(widget, QtWidgets.QLineEdit):
        return (
            widget.selectionStart(),
            widget.selectionStart() + len(widget.selectedText()))
    else:
        assert False, 'Unknown widget type'


def _get_widget_text(widget):
    if isinstance(widget, QtWidgets.QPlainTextEdit):
        return widget.toPlainText()
    elif isinstance(widget, QtWidgets.QLineEdit):
        return widget.text()
    else:
        assert False, 'Unknown widget type'


def _set_widget_text(widget, text):
    if isinstance(widget, QtWidgets.QPlainTextEdit):
        widget.document().setPlainText(text)
    elif isinstance(widget, QtWidgets.QLineEdit):
        widget.setText(text)
    else:
        assert False, 'Unknown widget type'


def _narrow_match(matches, idx, selected_idx, direction, subject_widget):
    if idx == selected_idx:
        selection_start, selection_end = (
            _get_selection_from_widget(subject_widget))
        if selection_end == selection_start:
            if direction > 0:
                return matches[0]
        elif direction > 0:
            for match in matches:
                if match.end() > selection_end:
                    return match
        elif direction < 0:
            for match in reversed(matches):
                if match.start() < selection_start:
                    return match
    elif direction > 0:
        return matches[0]
    elif direction < 0:
        return matches[-1]


def _search(api, main_window, regex, mode, direction):
    num_lines = len(api.subs.lines)
    if not api.subs.has_selection:
        selected_idx = None
        iterator = range(num_lines)
        if direction < 0:
            iterator = reversed(iterator)
    else:
        selected_idx = api.subs.selected_indexes[0]
        iterator = list(
            (selected_idx + direction * i) % num_lines
            for i in range(num_lines)
        )

    for idx in iterator:
        subject = _get_subject_text_by_mode(api.subs.lines[idx], mode)
        matches = list(re.finditer(regex, subject))
        if not matches:
            continue

        subject_widget = _get_subject_widget_by_mode(main_window, mode)
        final_match = _narrow_match(
            matches, idx, selected_idx, direction, subject_widget)

        if not final_match:
            continue

        api.subs.selected_indexes = [idx]

        _select_text_on_widget(
            subject_widget, final_match.start(), final_match.end())
        return True

    return False


def _replace_selection(main_window, new_text, mode):
    subject_widget = _get_subject_widget_by_mode(main_window, mode)
    selection_start, selection_end = _get_selection_from_widget(subject_widget)
    old_subject = _get_widget_text(subject_widget)
    new_subject = (
        old_subject[:selection_start]
        + new_text
        + old_subject[selection_end:])
    _set_widget_text(subject_widget, new_subject)


def _replace_all(api, regex, new_text, mode):
    with api.undo.bulk():
        count = 0
        for sub in api.subs.lines:
            old_subject_text = _get_subject_text_by_mode(sub, mode)
            new_subject_text = re.sub(regex, new_text, old_subject_text)
            if old_subject_text != new_subject_text:
                _set_subject_text_by_mode(sub, mode, new_subject_text)
                count += len(re.findall(regex, old_subject_text))
        if count:
            api.subs.selected_indexes = []
        return count


def _count(api, regex, mode):
    count = 0
    for sub in api.subs.lines:
        subject_text = _get_subject_text_by_mode(sub, mode)
        count += len(re.findall(regex, subject_text))
    return count


class SearchModeGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent):
        super().__init__('Search mode:', parent)
        self._radio_buttons = {
            SearchMode.Text: QtWidgets.QRadioButton('Text', self),
            SearchMode.Note: QtWidgets.QRadioButton('Note', self),
            SearchMode.Actor: QtWidgets.QRadioButton('Actor', self),
            SearchMode.Style: QtWidgets.QRadioButton('Style', self),
        }
        layout = QtWidgets.QVBoxLayout(self)
        for radio_button in self._radio_buttons.values():
            layout.addWidget(radio_button)
        self._radio_buttons[SearchMode.Text].setChecked(True)

    def set_value(self, value):
        self._radio_buttons[value].setChecked(True)

    def get_value(self):
        for key, radio_button in self._radio_buttons.items():
            if radio_button.isChecked():
                return key
        return None


class SearchDialog(QtWidgets.QDialog):
    def __init__(
            self,
            api,
            main_window,
            show_replace_controls,
            parent=None):
        super().__init__(parent)
        self._main_window = main_window
        self._api = api

        self.search_text_edit = QtWidgets.QComboBox(
            self,
            editable=True,
            maxCount=MAX_HISTORY_ENTRIES,
            sizePolicy=QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Preferred),
            insertPolicy=QtWidgets.QComboBox.NoInsert)
        completer = self.search_text_edit.completer()
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.search_text_edit.setCompleter(completer)

        self.replacement_text_edit = QtWidgets.QLineEdit(self)
        self.case_chkbox = QtWidgets.QCheckBox('Case sensitivity', self)
        self.regex_chkbox = QtWidgets.QCheckBox(
            'Use regular expressions', self)
        self.search_mode_group_box = SearchModeGroupBox(self)

        search_label = QtWidgets.QLabel('Text to search for:', self)
        replace_label = QtWidgets.QLabel('Text to replace with:', self)

        strip = QtWidgets.QDialogButtonBox(
            self, orientation=QtCore.Qt.Vertical)
        self.find_next_btn = strip.addButton('Find next', strip.ActionRole)
        self.find_prev_btn = strip.addButton('Find previous', strip.ActionRole)
        self.count_btn = strip.addButton('Count occurences', strip.ActionRole)
        self.replace_sel_btn = strip.addButton(
            'Replace selection', strip.ActionRole)
        self.replace_all_btn = strip.addButton('Replace all', strip.ActionRole)
        strip.addButton('Cancel', strip.RejectRole)
        strip.clicked.connect(self.action)
        strip.rejected.connect(self.reject)

        self._load_opt()
        self._update_replacement_enabled()

        settings_box = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(settings_box, spacing=16)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(search_label)
        layout.addWidget(self.search_text_edit)
        layout.addWidget(replace_label)
        layout.addWidget(self.replacement_text_edit)
        layout.addWidget(self.case_chkbox)
        layout.addWidget(self.regex_chkbox)
        layout.addWidget(self.search_mode_group_box)
        layout.addWidget(strip)

        if not show_replace_controls:
            replace_label.hide()
            self.replacement_text_edit.hide()
            self.replace_sel_btn.hide()
            self.replace_all_btn.hide()

        layout = QtWidgets.QHBoxLayout(self, spacing=24)
        layout.addWidget(settings_box)
        layout.addWidget(strip)

        self.search_text_edit.lineEdit().selectAll()

    def reject(self, *args):
        self._save_opt()
        return super().reject(*args)

    def action(self, sender):
        self._save_opt()
        if sender == self.replace_sel_btn:
            self._replace_selection()
        elif sender == self.replace_all_btn:
            self._replace_all()
        elif sender == self.find_prev_btn:
            self._search(-1)
        elif sender == self.find_next_btn:
            self._search(1)
        elif sender == self.count_btn:
            self._count()

    def _replace_selection(self):
        _replace_selection(self._main_window, self._target_text, self._mode)
        self._update_replacement_enabled()

    def _replace_all(self):
        self._push_search_history()
        count = _replace_all(
            self._api,
            self._search_regex,
            self._target_text,
            self._mode)
        bubblesub.ui.util.notice(
            f'Replaced {count} occurences.'
            if count
            else 'No occurences found.')

    def _search(self, direction):
        self._push_search_history()
        result = _search(
            self._api,
            self._main_window,
            self._search_regex,
            self._mode,
            direction)
        if not result:
            bubblesub.ui.util.notice('No occurences found.')
        self._update_replacement_enabled()

    def _count(self):
        self._push_search_history()
        count = _count(self._api, self._search_regex, self._mode)
        bubblesub.ui.util.notice(
            f'Found {count} occurences.' if count else 'No occurences found.')

    def _update_replacement_enabled(self):
        mode = self._mode
        subject_widget = _get_subject_widget_by_mode(self._main_window, mode)
        selection_start, selection_end = _get_selection_from_widget(
            subject_widget)
        self.replace_sel_btn.setEnabled(selection_start != selection_end)

    def _push_search_history(self):
        text = self._text  # binding it to a variable is important
        idx = self.search_text_edit.findText(text)
        if idx is not None:
            self.search_text_edit.removeItem(idx)
        self.search_text_edit.insertItem(0, text)
        self.search_text_edit.setCurrentIndex(0)

    def _load_opt(self):
        self.search_text_edit.clear()
        self.search_text_edit.addItems(
            [item for item in self._opt['history'] if item])
        self.case_chkbox.setChecked(self._opt['case_sensitive'])
        self.regex_chkbox.setChecked(self._opt['use_regexes'])
        self.search_mode_group_box.set_value(self._opt['mode'])

    def _save_opt(self):
        self._opt['history'] = [
            self.search_text_edit.itemText(i)
            for i in range(self.search_text_edit.count())]
        self._opt['use_regexes'] = self.regex_chkbox.isChecked()
        self._opt['case_sensitive'] = self.case_chkbox.isChecked()
        self._opt['mode'] = self.search_mode_group_box.get_value()

    @property
    def _opt(self):
        return self._api.opt.general['search']

    @property
    def _text(self):
        return self.search_text_edit.currentText()

    @property
    def _target_text(self):
        return self.replacement_text_edit.text()

    @property
    def _use_regexes(self):
        return self.regex_chkbox.isChecked()

    @property
    def _case_sensitive(self):
        return self.case_chkbox.isChecked()

    @property
    def _mode(self):
        return self.search_mode_group_box.get_value()

    @property
    def _search_regex(self):
        return _create_search_regex(
            self._text, self._case_sensitive, self._use_regexes)


class SearchCommand(CoreCommand):
    name = 'edit/search'
    menu_name = 'Search...'

    async def run(self):
        async def run(api, main_window):
            SearchDialog(api, main_window, show_replace_controls=False).exec_()

        await self.api.gui.exec(run)


class SearchAndReplaceCommand(CoreCommand):
    name = 'edit/search-and-replace'
    menu_name = 'Search and replace...'

    async def run(self):
        async def run(api, main_window):
            SearchDialog(api, main_window, show_replace_controls=True).exec_()

        await self.api.gui.exec(run)


class SearchRepeatCommand(CoreCommand):
    name = 'edit/search-repeat'

    def __init__(self, api, direction):
        super().__init__(api)
        self._direction = direction

    @property
    def menu_name(self):
        return 'Search %s' % ['previous', 'next'][self._direction > 0]

    @property
    def is_enabled(self):
        return len(self.api.opt.general['search']['history']) > 0

    async def run(self):
        async def run(api, main_window):
            opt = self.api.opt.general['search']
            result = _search(
                api,
                main_window,
                _create_search_regex(
                    opt['history'][0],
                    opt['case_sensitive'],
                    opt['use_regexes']),
                opt['mode'],
                self._direction)
            if not result:
                bubblesub.ui.util.notice('No occurences found.')

        await self.api.gui.exec(run)
