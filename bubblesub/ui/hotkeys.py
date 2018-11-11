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

import functools
import typing as T

from PyQt5 import QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandError
from bubblesub.opt.hotkeys import Hotkey, HotkeyContext


def setup_hotkeys(
    api: Api,
    context_to_widget_map: T.Dict[HotkeyContext, QtWidgets.QWidget],
    hotkeys_def: T.Iterable[T.Tuple[HotkeyContext, T.List[Hotkey]]],
) -> None:
    main_widget = context_to_widget_map[HotkeyContext.Global]
    for shortcut in main_widget.findChildren(QtWidgets.QShortcut):
        shortcut.setParent(None)

    key_sequences: T.List[str] = []
    cmd_map: T.Dict[T.Tuple[QtWidgets.QWidget, str], T.List[BaseCommand]] = {}

    for context, hotkeys in hotkeys_def:
        parent = context_to_widget_map[context]
        for hotkey in hotkeys:
            # parse cmdline here to report configuration errors early
            try:
                cmds = api.cmd.parse_cmdline(hotkey.cmdline)
            except CommandError as ex:
                api.log.error(str(ex))
                continue

            cmd_map[parent, hotkey.shortcut] = cmds
            key_sequences.append(hotkey.shortcut)

    def _on_activate(keys: str) -> None:
        widget = QtWidgets.QApplication.focusWidget()
        while widget:
            if (widget, keys) in cmd_map:
                cmds = cmd_map[widget, keys]
                for cmd in cmds:
                    api.cmd.run(cmd)
                break
            widget = widget.parent()

    for key_sequence in key_sequences:
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(key_sequence), main_widget
        )
        shortcut.activatedAmbiguously.connect(shortcut.activated.emit)
        shortcut.activated.connect(
            functools.partial(_on_activate, key_sequence)
        )
