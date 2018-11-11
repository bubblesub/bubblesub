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
import traceback
import typing as T

from PyQt5 import QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import CommandError
from bubblesub.opt.hotkeys import HotkeyContext
from bubblesub.opt.menu import MenuCommand
from bubblesub.opt.menu import MenuItem
from bubblesub.opt.menu import MenuSeparator
from bubblesub.opt.menu import SubMenu


HotkeyMap = T.Dict[T.Tuple[HotkeyContext, str], str]


def _window_from_menu(menu: QtWidgets.QMenu) -> QtWidgets.QWidget:
    window = menu
    while window.parent() is not None:
        window = window.parent()
    return window


def _on_menu_about_to_show(menu: QtWidgets.QMenu) -> None:
    window = _window_from_menu(menu)
    window.setProperty('focused-widget', window.focusWidget())
    for action in menu.actions():
        if getattr(action, 'commands', None):
            try:
                action.setEnabled(
                    all(cmd.is_enabled for cmd in action.commands)
                )
            except Exception:  # pylint: disable=broad-except
                traceback.print_exc()
                action.setEnabled(False)


def _on_menu_about_to_hide(menu: QtWidgets.QMenu) -> None:
    window = _window_from_menu(menu)
    focused_widget = window.property('focused-widget')
    if focused_widget:
        focused_widget.setFocus()


class _CommandAction(QtWidgets.QAction):
    def __init__(
            self,
            api: Api,
            item: MenuCommand,
            parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self.api = api
        self.commands = api.cmd.parse_cmdline(item.cmdline)
        self.triggered.connect(self._on_trigger)
        self.setText(item.name)

    def _on_trigger(self) -> None:
        for cmd in self.commands:
            self.api.cmd.run(cmd)


def _build_hotkey_map(api: Api) -> HotkeyMap:
    ret: HotkeyMap = {}
    for context, hotkeys in api.opt.hotkeys:
        for hotkey in hotkeys:
            ret[context, hotkey.cmdline] = hotkey.shortcut
    return ret


def setup_cmd_menu(
        api: Api,
        parent: QtWidgets.QWidget,
        menu_def: T.Sequence[MenuItem],
        context: HotkeyContext
) -> T.Any:
    hotkey_map = _build_hotkey_map(api)
    stack = [(parent, menu_def)]

    while stack:
        parent, menu_def = stack.pop()

        if hasattr(parent, 'aboutToShow'):
            parent.aboutToShow.connect(
                functools.partial(_on_menu_about_to_show, parent)
            )
            parent.aboutToHide.connect(
                functools.partial(_on_menu_about_to_hide, parent)
            )

        for item in menu_def:
            if isinstance(item, MenuSeparator):
                parent.addSeparator()
            elif isinstance(item, SubMenu):
                stack.append((parent.addMenu(item.name), item.children))
            elif isinstance(item, MenuCommand):
                try:
                    action = _CommandAction(api, item, parent)
                except CommandError as ex:
                    api.log.error(str(ex))
                    continue

                shortcut = hotkey_map.get((context, item.cmdline))
                if shortcut is not None:
                    action.setText(action.text() + '\t' + shortcut)

                parent.addAction(action)
            else:
                api.log.error(f'unexpected menu item {item}')
