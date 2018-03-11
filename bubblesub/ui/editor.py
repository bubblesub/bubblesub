import enchant

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.util


class SpellCheckHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, api, *args):
        super().__init__(*args)

        spell_check_lang = api.opt.general['spell_check']
        try:
            self._dictionary = (
                enchant.Dict(spell_check_lang)
                if spell_check_lang
                else None)
        except enchant.errors.DictNotFoundError:
            self._dictionary = None
            api.log.warn(f'dictionary {spell_check_lang} not installed.')

        self._fmt = QtGui.QTextCharFormat()
        self._fmt.setUnderlineColor(QtCore.Qt.red)
        self._fmt.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
        self._fmt.setFontUnderline(True)

    def highlightBlock(self, text):
        if not self._dictionary:
            return

        for start, end, _match in bubblesub.util.spell_check_ass_line(
                self._dictionary, text):
            self.setFormat(start, end - start, self._fmt)


class TextEdit(QtWidgets.QPlainTextEdit):
    def __init__(self, api, name, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._name = name
        self._api = api
        try:
            font_def = self._api.opt.general['fonts'][name]
            if font_def:
                font = QtGui.QFont()
                font.fromString(font_def)
                self.setFont(font)
        except KeyError:
            pass

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
            distance = 1 if event.angleDelta().y() > 0 else -1
            new_size = self.font().pointSize() + distance
            if new_size < 5:
                return
            font = self.font()
            font.setPointSize(new_size)
            self.setFont(font)
            self._api.opt.general['fonts'][self._name] = (
                self.font().toString())


class TopBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.start_time_edit = bubblesub.ui.util.TimeEdit(self)
        self.end_time_edit = bubblesub.ui.util.TimeEdit(self)
        self.duration_edit = bubblesub.ui.util.TimeEdit(self)

        self.margins_widget = QtWidgets.QWidget(self)
        self.margin_l_edit = QtWidgets.QSpinBox(
            self.margins_widget, minimum=0, maximum=999)
        self.margin_v_edit = QtWidgets.QSpinBox(
            self.margins_widget, minimum=0, maximum=999)
        self.margin_r_edit = QtWidgets.QSpinBox(
            self.margins_widget, minimum=0, maximum=999)
        layout = QtWidgets.QHBoxLayout(self.margins_widget, spacing=0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.margin_l_edit)
        layout.addWidget(self.margin_v_edit)
        layout.addWidget(self.margin_r_edit)

        self.layer_edit = QtWidgets.QSpinBox(self, minimum=0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel('Start time:', self))
        layout.addWidget(self.start_time_edit)
        layout.addWidget(QtWidgets.QLabel('End time:', self))
        layout.addWidget(self.end_time_edit)
        layout.addWidget(QtWidgets.QLabel('Duration:', self))
        layout.addWidget(self.duration_edit)
        layout.addStretch()
        layout.addWidget(QtWidgets.QLabel('Margins:', self))
        layout.addWidget(self.margins_widget)
        layout.addWidget(QtWidgets.QLabel('Layer:', self))
        layout.addWidget(self.layer_edit)


class CenterBar(QtWidgets.QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)

        self.text_edit = TextEdit(
            api, 'editor', self,
            tabChangesFocus=True)
        self.note_edit = TextEdit(
            api, 'notes', self,
            tabChangesFocus=True,
            placeholderText='Notes')

        self.text_edit.highlighter = \
            SpellCheckHighlighter(api, self.text_edit.document())

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.note_edit)


class BottomBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.style_edit = QtWidgets.QComboBox(
            self,
            editable=True,
            sizePolicy=QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Preferred),
            insertPolicy=QtWidgets.QComboBox.NoInsert)
        self.actor_edit = QtWidgets.QComboBox(
            self,
            editable=True,
            sizePolicy=QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Preferred),
            insertPolicy=QtWidgets.QComboBox.NoInsert)
        self.effect_edit = QtWidgets.QLineEdit(self)
        self.comment_checkbox = QtWidgets.QCheckBox('Comment', self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel('Style:', self))
        layout.addWidget(self.style_edit)
        layout.addWidget(QtWidgets.QLabel('Actor:', self))
        layout.addWidget(self.actor_edit)
        layout.addStretch()
        layout.addWidget(QtWidgets.QLabel('Effect:', self))
        layout.addWidget(self.effect_edit)
        layout.addWidget(self.comment_checkbox)


class Editor(QtWidgets.QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)

        self._index = None
        self._api = api

        self.top_bar = TopBar(self)
        self.center = CenterBar(api, self)
        self.bottom_bar = BottomBar(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.top_bar)
        layout.addWidget(self.center)
        layout.addWidget(self.bottom_bar)
        self.setEnabled(False)

        self._connect_api_signals()
        self._connect_ui_signals()

    def _fetch_selection(self, index):
        self._index = index
        subtitle = self._api.subs.lines[index]
        self.top_bar.start_time_edit.set_value(subtitle.start)
        self.top_bar.end_time_edit.set_value(subtitle.end)
        self.top_bar.duration_edit.set_value(subtitle.duration)
        self.bottom_bar.effect_edit.setText(subtitle.effect)
        self.top_bar.layer_edit.setValue(subtitle.layer)
        self.bottom_bar.comment_checkbox.setChecked(subtitle.is_comment)
        self.top_bar.margin_l_edit.setValue(subtitle.margins[0])
        self.top_bar.margin_v_edit.setValue(subtitle.margins[1])
        self.top_bar.margin_r_edit.setValue(subtitle.margins[2])

        self.bottom_bar.actor_edit.clear()
        self.bottom_bar.actor_edit.addItems(
            sorted(list(set(sub.actor for sub in self._api.subs.lines))))
        self.bottom_bar.actor_edit.lineEdit().setText(subtitle.actor)

        self.bottom_bar.style_edit.clear()
        self.bottom_bar.style_edit.addItems(
            sorted(list(set(sub.style for sub in self._api.subs.lines))))
        self.bottom_bar.style_edit.lineEdit().setText(subtitle.style)

        self.center.text_edit.document().setPlainText(
            self._convert_newlines(subtitle.text))
        self.center.note_edit.document().setPlainText(
            self._convert_newlines(subtitle.note))
        self.setEnabled(True)

    def _convert_newlines(self, text):
        if self._api.opt.general['convert_newlines']:
            return text.replace('\\N', '\n')
        return text

    def _clear_selection(self):
        self._index = None
        self.top_bar.start_time_edit.reset_text()
        self.top_bar.end_time_edit.reset_text()
        self.top_bar.duration_edit.reset_text()
        self.bottom_bar.style_edit.lineEdit().setText('')
        self.bottom_bar.actor_edit.lineEdit().setText('')
        self.bottom_bar.effect_edit.setText('')
        self.top_bar.layer_edit.setValue(0)
        self.bottom_bar.comment_checkbox.setChecked(False)
        self.top_bar.margin_l_edit.setValue(0)
        self.top_bar.margin_v_edit.setValue(0)
        self.top_bar.margin_r_edit.setValue(0)
        self.center.text_edit.document().setPlainText('')
        self.center.note_edit.document().setPlainText('')
        self.setEnabled(False)

    def _push_selection(self):
        if not self.isEnabled():
            return

        self._disconnect_api_signals()
        subtitle = self._api.subs.lines[self._index]
        subtitle.begin_update()
        subtitle.start = self.top_bar.start_time_edit.get_value()
        subtitle.end = self.top_bar.end_time_edit.get_value()
        subtitle.style = self.bottom_bar.style_edit.lineEdit().text()
        subtitle.actor = self.bottom_bar.actor_edit.lineEdit().text()
        subtitle.text = (
            self.center.text_edit.toPlainText().replace('\n', r'\N'))
        subtitle.note = (
            self.center.note_edit.toPlainText().replace('\n', r'\N'))
        subtitle.effect = self.bottom_bar.effect_edit.text()
        subtitle.layer = self.top_bar.layer_edit.value()
        subtitle.margins = (
            self.top_bar.margin_l_edit.value(),
            self.top_bar.margin_v_edit.value(),
            self.top_bar.margin_r_edit.value())
        subtitle.is_comment = self.bottom_bar.comment_checkbox.isChecked()
        subtitle.end_update()
        self._connect_api_signals()

    def _on_grid_selection_change(self, rows, _changed):
        self._disconnect_ui_signals()
        if len(rows) == 1:
            self._fetch_selection(rows[0])
        else:
            self._clear_selection()
        self._connect_ui_signals()

    def _on_items_insert(self, idx, count):
        if self._index in range(idx, idx + count):
            self._disconnect_ui_signals()
            self._fetch_selection(self._index)
            self._connect_ui_signals()

    def _on_items_remove(self, idx, count):
        if self._index in range(idx, idx + count):
            self._disconnect_ui_signals()
            self._clear_selection()
            self._connect_ui_signals()

    def _on_item_change(self, idx):
        if idx == self._index or idx is None:
            self._disconnect_ui_signals()
            self._fetch_selection(self._index)
            self._connect_ui_signals()

    def _on_time_end_edit(self):
        self._disconnect_ui_signals()
        start = self.top_bar.start_time_edit.get_value()
        end = self.top_bar.end_time_edit.get_value()
        duration = end - start
        self.top_bar.duration_edit.set_value(duration)
        self._push_selection()
        self._connect_ui_signals()

    def _on_duration_edit(self):
        self._disconnect_ui_signals()
        start = self.top_bar.start_time_edit.get_value()
        duration = self.top_bar.duration_edit.get_value()
        end = start + duration
        self.top_bar.end_time_edit.set_value(end)
        self._push_selection()
        self._connect_ui_signals()

    def _on_generic_edit(self):
        self._push_selection()

    def _connect_api_signals(self):
        self._api.subs.lines.items_inserted.connect(self._on_items_insert)
        self._api.subs.lines.items_removed.connect(self._on_items_remove)
        self._api.subs.lines.item_changed.connect(self._on_item_change)
        self._api.subs.selection_changed.connect(
            self._on_grid_selection_change)

    def _disconnect_api_signals(self):
        self._api.subs.lines.items_inserted.disconnect(self._on_items_insert)
        self._api.subs.lines.items_removed.disconnect(self._on_items_remove)
        self._api.subs.lines.item_changed.disconnect(self._on_item_change)
        self._api.subs.selection_changed.disconnect(
            self._on_grid_selection_change)

    # TODO: get rid of this crap

    def _connect_ui_signals(self):
        self.top_bar.start_time_edit.textEdited.connect(self._on_generic_edit)
        self.top_bar.end_time_edit.textEdited.connect(self._on_time_end_edit)
        self.top_bar.duration_edit.textEdited.connect(self._on_duration_edit)
        self.bottom_bar.actor_edit.editTextChanged.connect(
            self._on_generic_edit)
        self.bottom_bar.style_edit.editTextChanged.connect(
            self._on_generic_edit)
        self.center.text_edit.textChanged.connect(self._on_generic_edit)
        self.center.note_edit.textChanged.connect(self._on_generic_edit)
        self.bottom_bar.effect_edit.textChanged.connect(self._on_generic_edit)
        self.top_bar.layer_edit.valueChanged.connect(self._on_generic_edit)
        self.top_bar.margin_l_edit.valueChanged.connect(self._on_generic_edit)
        self.top_bar.margin_v_edit.valueChanged.connect(self._on_generic_edit)
        self.top_bar.margin_r_edit.valueChanged.connect(self._on_generic_edit)
        self.bottom_bar.comment_checkbox.stateChanged.connect(
            self._on_generic_edit)

    def _disconnect_ui_signals(self):
        self.top_bar.start_time_edit.textEdited.disconnect(
            self._on_generic_edit)
        self.top_bar.end_time_edit.textEdited.disconnect(
            self._on_time_end_edit)
        self.top_bar.duration_edit.textEdited.disconnect(
            self._on_duration_edit)
        self.bottom_bar.actor_edit.editTextChanged.disconnect(
            self._on_generic_edit)
        self.bottom_bar.style_edit.editTextChanged.disconnect(
            self._on_generic_edit)
        self.center.text_edit.textChanged.disconnect(self._on_generic_edit)
        self.center.note_edit.textChanged.disconnect(self._on_generic_edit)
        self.bottom_bar.effect_edit.textChanged.disconnect(
            self._on_generic_edit)
        self.top_bar.layer_edit.valueChanged.disconnect(self._on_generic_edit)
        self.top_bar.margin_l_edit.valueChanged.disconnect(
            self._on_generic_edit)
        self.top_bar.margin_v_edit.valueChanged.disconnect(
            self._on_generic_edit)
        self.top_bar.margin_r_edit.valueChanged.disconnect(
            self._on_generic_edit)
        self.bottom_bar.comment_checkbox.stateChanged.disconnect(
            self._on_generic_edit)
