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

from functools import partial
from typing import Optional, Union

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication, QShortcut, QWidget

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandError
from bubblesub.cfg.hotkeys import Hotkey, HotkeyContext


class HotkeyManager:
    def __init__(
        self, api: Api, context_map: dict[HotkeyContext, QWidget]
    ) -> None:
        self._api = api
        self._hotkey_context_map = context_map

        self._cmd_map: dict[
            tuple[QWidget, str],
            tuple[QShortcut, list[BaseCommand]],
        ] = {}

        self._rebuild()

        api.cmd.commands_loaded.connect(self._rebuild)
        api.cfg.hotkeys.changed.connect(self._on_hotkey_change)
        api.cfg.hotkeys.added.connect(self._on_hotkey_add)
        api.cfg.hotkeys.deleted.connect(self._on_hotkey_delete)

    def _rebuild(self) -> None:
        for qt_shortcut, _cmds in self._cmd_map.values():
            qt_shortcut.setEnabled(False)
        self._cmd_map.clear()

        for hotkey in self._api.cfg.hotkeys:
            self._set_hotkey(hotkey.context, hotkey.shortcut, hotkey.cmdline)

    def _on_hotkey_add(self, hotkey: Hotkey) -> None:
        self._set_hotkey(hotkey.context, hotkey.shortcut, hotkey.cmdline)

    def _on_hotkey_delete(self, hotkey: Hotkey) -> None:
        self._set_hotkey(hotkey.context, hotkey.shortcut, None)

    def _on_hotkey_change(self, hotkey: Hotkey) -> None:
        self._set_hotkey(hotkey.context, hotkey.shortcut, hotkey.cmdline)

    def _set_hotkey(
        self,
        context: HotkeyContext,
        shortcut: str,
        cmdline: Optional[Union[str, list[list[str]]]],
    ) -> None:
        widget = self._hotkey_context_map[context]
        shortcut = shortcut.lower()

        if cmdline is None:
            if result := self._cmd_map.pop((widget, shortcut), None):
                qt_shortcut, _cmds = result
                qt_shortcut.setEnabled(False)
            return

        # parse cmdline here to report configuration errors early
        try:
            cmds = self._api.cmd.parse_cmdline(cmdline)
        except CommandError as ex:
            self._api.log.error(str(ex))
            return

        def _on_activate(keys: str) -> None:
            widget = QApplication.focusWidget()
            if not widget:
                widget = self._hotkey_context_map[HotkeyContext.GLOBAL]
            while widget:
                if (widget, keys) in self._cmd_map:
                    _qt_shortcut, cmds = self._cmd_map[widget, keys]
                    for cmd in cmds:
                        self._api.cmd.run(cmd)
                    break
                widget = widget.parentWidget()

        qt_shortcut = QShortcut(QKeySequence(shortcut), widget)
        qt_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        qt_shortcut.activatedAmbiguously.connect(qt_shortcut.activated.emit)
        qt_shortcut.activated.connect(partial(_on_activate, shortcut))

        self._cmd_map[widget, shortcut] = (qt_shortcut, cmds)
