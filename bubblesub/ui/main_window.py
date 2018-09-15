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

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import bubblesub.ui.audio
import bubblesub.ui.console
import bubblesub.ui.editor
import bubblesub.ui.statusbar
import bubblesub.ui.subs_grid
import bubblesub.ui.util
import bubblesub.ui.video
from bubblesub.api import Api
from bubblesub.opt.hotkeys import HotkeyContext
from bubblesub.opt.menu import MenuCommand
from bubblesub.opt.menu import MenuContext
from bubblesub.opt.menu import MenuSeparator
from bubblesub.opt.menu import SubMenu
from bubblesub.ui.hotkeys import setup_hotkeys
from bubblesub.ui.menu import setup_cmd_menu


class MainWindow(QtWidgets.QMainWindow):
    def __init__(
            self,
            api: Api,
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
        api.cmd.commands_loaded.connect(self._rebuild_menu)
        api.cmd.commands_loaded.connect(self._rebuild_hotkeys)

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
        self.video.layout().setContentsMargins(0, 0, 2, 0)
        self.editor_splitter.setContentsMargins(2, 0, 0, 0)

        self.console_splitter = QtWidgets.QSplitter(self)
        self.console = console
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

        self._rebuild_menu()
        self._rebuild_hotkeys()

        self.setCentralWidget(self.main_splitter)
        self.setStatusBar(self.status_bar)

        self.apply_palette(T.cast(str, api.opt.general.gui.current_palette))

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
            self.audio.shutdown()
            self.video.shutdown()
            event.accept()

    def apply_palette(self, palette_name: str) -> None:
        try:
            palette_def = self._api.opt.general.gui.palettes[palette_name]
        except KeyError:
            raise ValueError(f'unknown palette: "{palette_name}"')

        self._api.opt.general.gui.current_palette = palette_name

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

    def _rebuild_menu(self) -> None:
        for action in self.menuBar().actions():
            self.menuBar().removeAction(action)

        setup_cmd_menu(
            self._api,
            self.menuBar(),
            self._api.opt.menu[MenuContext.MainMenu] +
            [
                SubMenu(
                    'Pl&ugins',
                    [
                        MenuCommand('Reload plugins', '/reload-cmds'),
                        MenuSeparator(),
                    ] + self._api.cmd.get_plugin_menu_items()
                )
            ],
            HotkeyContext.Global
        )

    def _rebuild_hotkeys(self) -> None:
        setup_hotkeys(
            self._api,
            {
                HotkeyContext.Global: self,
                HotkeyContext.Spectrogram: self.audio,
                HotkeyContext.SubtitlesGrid: self.subs_grid,
            },
            self._api.opt.hotkeys
        )

    def _restore_splitters(self) -> None:
        def _load(widget: QtWidgets.QWidget, key: str) -> None:
            data = self._api.opt.general.gui.splitters.get(key, None)
            if data:
                widget.restoreState(data)

        _load(self.top_bar, 'top')
        _load(self.editor_splitter, 'editor')
        _load(self.main_splitter, 'main')
        _load(self.console_splitter, 'console')

    def _store_splitters(self) -> None:
        self._api.opt.general.gui.splitters = {
            'top': self.top_bar.saveState(),
            'editor': self.editor_splitter.saveState(),
            'main': self.main_splitter.saveState(),
            'console': self.console_splitter.saveState(),
        }

    def _update_title(self) -> None:
        self.setWindowTitle(
            f'bubblesub - {self._api.subs.path}'
            if self._api.subs.path else
            'bubblesub'
        )
