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

import base64
import functools
import typing as T

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.audio
import bubblesub.ui.console
import bubblesub.ui.editor
import bubblesub.ui.statusbar
import bubblesub.ui.subs_grid
import bubblesub.ui.util
import bubblesub.ui.video
from bubblesub.opt.hotkeys import Hotkey
from bubblesub.opt.menu import MenuCommand
from bubblesub.opt.menu import MenuItem
from bubblesub.opt.menu import MenuSeparator


def _load_splitter_state(
        widget: QtWidgets.QWidget,
        opt: T.Dict[str, str],
        key: str
) -> None:
    data = opt.get(key, None)
    if data:
        widget.restoreState(base64.b64decode(data))


def _get_splitter_state(widget: QtWidgets.QWidget) -> str:
    return base64.b64encode(widget.saveState()).decode('ascii')


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self,
            api: bubblesub.api.Api,
            console: 'bubblesub.ui.console.Console'
    ) -> None:
        super().__init__()

        self._api = api
        self._update_title()

        api.gui.quit_requested.connect(self.close)
        api.gui.begin_update_requested.connect(
            lambda: self.setUpdatesEnabled(False)
        )
        api.gui.end_update_requested.connect(
            lambda: self.setUpdatesEnabled(True)
        )
        api.subs.loaded.connect(self._update_title)
        api.cmd.plugins_loaded.connect(self._setup_plugins_menu)

        self.video = bubblesub.ui.video.Video(api, self)
        self.audio = bubblesub.ui.audio.Audio(api, self)
        self.editor = bubblesub.ui.editor.Editor(api, self)
        self.subs_grid = bubblesub.ui.subs_grid.SubsGrid(api, self)
        self.status_bar = bubblesub.ui.statusbar.StatusBar(api, self)

        self.editor_splitter = QtWidgets.QSplitter(self)
        self.editor_splitter.setOrientation(QtCore.Qt.Vertical)
        self.editor_splitter.addWidget(self.audio)
        self.editor_splitter.addWidget(self.editor)
        self.editor_splitter.setStretchFactor(0, 4)
        self.editor_splitter.setStretchFactor(1, 1)

        self.top_bar = QtWidgets.QSplitter(self)
        self.top_bar.setOrientation(QtCore.Qt.Horizontal)
        self.top_bar.addWidget(self.video)
        self.top_bar.addWidget(self.editor_splitter)
        self.top_bar.setStretchFactor(0, 1)
        self.top_bar.setStretchFactor(1, 1)

        self.console_splitter = QtWidgets.QSplitter(self)
        console.setParent(self.console_splitter)
        self.console_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.console_splitter.addWidget(self.subs_grid)
        self.console_splitter.addWidget(console)
        self.console_splitter.setStretchFactor(0, 2)
        self.console_splitter.setStretchFactor(1, 1)

        self.main_splitter = QtWidgets.QSplitter(self)
        self.main_splitter.setOrientation(QtCore.Qt.Vertical)
        self.main_splitter.addWidget(self.top_bar)
        self.main_splitter.addWidget(self.console_splitter)
        self.main_splitter.setContentsMargins(8, 8, 8, 8)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 5)

        action_map = self._setup_menu()
        self._setup_hotkeys(action_map)
        self._setup_plugins_menu()

        self.setCentralWidget(self.main_splitter)
        self.setStatusBar(self.status_bar)

        self.apply_palette(T.cast(str, api.opt.general.current_palette))

        self.subs_grid.setFocus()
        self.subs_grid.restore_grid_columns()
        self._restore_splitters()

    def changeEvent(self, _event: QtCore.QEvent) -> None:
        bubblesub.ui.util.get_color.cache_clear()

    def closeEvent(self, event: QtCore.QEvent) -> None:
        self.subs_grid.store_grid_columns()
        self._store_splitters()
        if self._api.undo.needs_save and not bubblesub.ui.util.ask(
                'There are unsaved changes. '
                'Are you sure you want to exit the program?'
        ):
            event.ignore()
        else:
            self.video.shutdown()
            event.accept()

    def apply_palette(self, palette_name: str) -> None:
        palette_def = self._api.opt.general.palettes[palette_name]
        palette = QtGui.QPalette()
        for color_type, color_value in palette_def.items():
            if '+' in color_type:
                group_name, role_name = color_type.split('+')
            else:
                group_name = ''
                role_name = color_type
            target_group = getattr(QtGui.QPalette, group_name, None)
            target_role = getattr(QtGui.QPalette, role_name, None)
            if target_group is not None and target_role is not None:
                palette.setColor(
                    target_group, target_role, QtGui.QColor(*color_value)
                )
            elif target_role is not None:
                palette.setColor(target_role, QtGui.QColor(*color_value))
        self.setPalette(palette)
        self.update()

    def _setup_menu(self) -> T.Any:
        return bubblesub.ui.util.setup_cmd_menu(
            self._api, self.menuBar(), self._api.opt.menu.main
        )

    def _setup_plugins_menu(self) -> None:
        plugins_menu_def: T.List[MenuItem] = [
            MenuCommand('misc/reload-plugins'),
            MenuSeparator(),
        ]
        plugins_menu_def += self._api.cmd.get_plugin_menu_items()
        for action in self.menuBar().children():
            if action.objectName() == 'plugins-menu':
                self.menuBar().removeAction(action.menuAction())
        plugins_menu = self.menuBar().addMenu('Pl&ugins')
        plugins_menu.setObjectName('plugins-menu')
        bubblesub.ui.util.setup_cmd_menu(
            self._api, plugins_menu, plugins_menu_def
        )

    def _setup_hotkeys(self, action_map: T.Any) -> None:
        shortcuts: T.Dict[T.Tuple[str, str], QtWidgets.QShortcut] = {}

        for context, hotkeys in self._api.opt.hotkeys:
            for hotkey in hotkeys:
                shortcut = self._setup_hotkey(
                    action_map, context, hotkey, shortcuts
                )
                if shortcut:
                    shortcuts[(hotkey.shortcut, context)] = shortcut

    def _setup_hotkey(
            self,
            action_map: T.Any,
            context: str,
            hotkey: Hotkey,
            shortcuts: T.Dict[T.Tuple[str, str], QtWidgets.QShortcut]
    ) -> QtWidgets.QShortcut:
        def resolve_ambiguity(keys: str) -> None:
            widget = QtWidgets.QApplication.focusWidget()
            while widget:
                try:
                    if widget == self.audio:
                        shortcuts[(keys, 'spectrogram')].activated.emit()
                except IndexError:
                    break
                widget = widget.parent()

        try:
            command = self._api.cmd.get(
                hotkey.command_name, hotkey.command_args
            )
        except KeyError:
            self._api.log.error(f'Unknown command {hotkey.command_name}')
            return None

        action = action_map.get((hotkey.command_name, *hotkey.command_args))
        if action and context == 'global':
            action.setText(
                action.text()
                + '\t'
                + QtGui.QKeySequence(hotkey.shortcut).toString()
            )

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(hotkey.shortcut), self
        )

        shortcut.activated.connect(
            functools.partial(self._api.cmd.run, command)
        )

        if context == 'spectrogram':
            shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            shortcut.setParent(self.audio)
        elif context == 'global':
            shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        else:
            raise RuntimeError(f'Invalid shortcut context "{context}"')

        shortcut.activatedAmbiguously.connect(
            functools.partial(resolve_ambiguity, hotkey.shortcut)
        )

        return shortcut

    def _restore_splitters(self) -> None:
        opt = self._api.opt.general.splitters
        if not opt:
            return
        _load_splitter_state(self.top_bar, opt, 'top')
        _load_splitter_state(self.editor_splitter, opt, 'editor')
        _load_splitter_state(self.main_splitter, opt, 'main')
        _load_splitter_state(self.console_splitter, opt, 'console')

    def _store_splitters(self) -> None:
        self._api.opt.general.splitters = {
            'top': _get_splitter_state(self.top_bar),
            'editor': _get_splitter_state(self.editor_splitter),
            'main': _get_splitter_state(self.main_splitter),
            'console': _get_splitter_state(self.console_splitter),
        }

    def _update_title(self) -> None:
        self.setWindowTitle(
            'bubblesub - {}'.format(self._api.subs.path)
            if self._api.subs.path else
            'bubblesub'
        )
