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

import asyncio
import functools
import typing as T
from pathlib import Path

from PyQt5 import QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import CommandError
from bubblesub.api.log import LogApi
from bubblesub.cfg.hotkeys import HotkeyContext
from bubblesub.cfg.menu import MenuItem
from bubblesub.ui.themes import BaseTheme

HotkeyMap = T.Dict[T.Tuple[HotkeyContext, str], str]


def _window_from_menu(menu: QtWidgets.QMenu) -> QtWidgets.QWidget:
    window = menu
    while window.parent() is not None:
        window = window.parent()
    return window


def _on_menu_about_to_show(log_api: LogApi, menu: QtWidgets.QMenu) -> None:
    window = _window_from_menu(menu)
    window.setProperty("focused-widget", window.focusWidget())
    for action in menu.actions():
        if getattr(action, "commands", None):
            enabled = False
            with log_api.exception_guard():
                enabled = all(cmd.is_enabled for cmd in action.commands)
            action.setEnabled(enabled)


def _on_menu_about_to_hide(menu: QtWidgets.QMenu) -> None:
    window = _window_from_menu(menu)
    focused_widget = window.property("focused-widget")
    if focused_widget:
        focused_widget.setFocus()


class CommandAction(QtWidgets.QAction):
    def __init__(
        self, api: Api, label: str, cmdline: str, parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self.api = api
        self.commands = api.cmd.parse_cmdline(cmdline)
        self.triggered.connect(self._on_trigger)
        self.setText(label)

    def _on_trigger(self) -> None:
        for cmd in self.commands:
            self.api.cmd.run(cmd)


class LoadRecentFileAction(QtWidgets.QAction):
    def __init__(
        self, api: Api, path: T.Union[str, Path], parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self.api = api
        self.path = path
        self.triggered.connect(self._on_trigger)
        self.setText(path)

    def _on_trigger(self) -> None:
        self.api.subs.load_ass(self.path)


class LoadThemeAction(QtWidgets.QAction):
    def __init__(
        self, api: Api, theme: T.Type[BaseTheme], parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self.api = api
        self.theme = theme
        self.triggered.connect(self._on_trigger)
        self.setText(f"Switch to &{theme.title} theme")

    def _on_trigger(self) -> None:
        asyncio.ensure_future(self._run())

    async def _run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        main_window.theme_mgr.apply_theme(self.theme.name)


def _build_hotkey_map(api: Api) -> HotkeyMap:
    ret: HotkeyMap = {}
    for hotkey in api.cfg.hotkeys:
        ret[hotkey.context, hotkey.cmdline] = hotkey.shortcut
    return ret


class MenuBuilder:
    def __init__(self, api: Api, context: HotkeyContext) -> None:
        self.api = api
        self.context = context
        self.hotkey_map = _build_hotkey_map(api)

    def build(self, parent: QtWidgets.QWidget, menu_item: MenuItem) -> None:
        method_name = "build_" + menu_item.type.value
        if hasattr(self, method_name):
            getattr(self, method_name)(parent, menu_item)
        else:
            self.api.log.error(f"unexpected menu item {menu_item.type.value}")

    def build_separator(
        self, parent: QtWidgets.QWidget, item: MenuItem
    ) -> None:
        parent.addSeparator()

    def build_recent_files(
        self, parent: QtWidgets.QWidget, item: MenuItem
    ) -> None:
        if item.label:
            parent = parent.addMenu(item.label)
        recent_files = self.api.cfg.opt.get("recent_files", [])
        if recent_files:
            for recent_file in recent_files:
                action = LoadRecentFileAction(self.api, recent_file, parent)
                parent.addAction(action)
        else:
            action = QtWidgets.QAction(parent)
            action.setText("(no recent files found)")
            action.setEnabled(False)
            parent.addAction(action)

    def build_plugins(self, parent: QtWidgets.QWidget, item: MenuItem) -> None:
        if item.label:
            parent = parent.addMenu(item.label)
        subitems = self.api.cmd.get_plugin_menu_items()
        if subitems:
            for subitem in subitems:
                self.build(parent, subitem)
        else:
            action = QtWidgets.QAction(parent)
            action.setText("(no plugins found)")
            action.setEnabled(False)
            parent.addAction(action)

    def build_themes(self, parent: QtWidgets.QWidget, item: MenuItem) -> None:
        if item.label:
            parent = parent.addMenu(item.label)
        for theme in BaseTheme.__subclasses__():
            action = LoadThemeAction(self.api, theme, parent)
            parent.addAction(action)

    def build_submenu(self, parent: QtWidgets.QWidget, item: MenuItem) -> None:
        submenu = parent.addMenu(item.label)
        for subitem in item.children or []:
            self.build(submenu, subitem)

    def build_placeholder(
        self, parent: QtWidgets.QWidget, item: MenuItem
    ) -> None:
        action = QtWidgets.QAction(parent)
        action.setText(item.label)
        action.setEnabled(False)
        parent.addAction(action)

    def build_command(self, parent: QtWidgets.QWidget, item: MenuItem) -> None:
        assert item.label
        assert item.cmdline

        try:
            action = CommandAction(self.api, item.label, item.cmdline, parent)
        except CommandError as ex:
            self.api.log.error(str(ex))
            return

        shortcut = self.hotkey_map.get((self.context, item.cmdline))
        if shortcut is not None:
            action.setText(action.text() + "\t" + shortcut)

        parent.addAction(action)


def setup_menu(
    api: Api,
    parent: QtWidgets.QWidget,
    root_item: MenuItem,
    context: HotkeyContext,
) -> T.Any:
    for action in parent.actions():
        parent.removeAction(action)

    if hasattr(parent, "aboutToShow"):
        parent.aboutToShow.connect(
            functools.partial(_on_menu_about_to_show, api.log, parent)
        )
        parent.aboutToHide.connect(
            functools.partial(_on_menu_about_to_hide, parent)
        )

    menu_builder = MenuBuilder(api, context)
    for node in root_item.children or []:
        menu_builder.build(parent, node)
