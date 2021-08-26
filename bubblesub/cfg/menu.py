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

"""Menu config."""

import enum
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from bubblesub.cfg.base import ConfigError, SubConfig
from bubblesub.data import DATA_DIR


def _get_user_path(root_dir: Path) -> Path:
    return root_dir / "menu.conf"


class MenuContext(enum.Enum):
    """Which GUI widget the menu appears in."""

    MAIN_MENU = "main"
    SUBTITLES_GRID = "subtitles_grid"


class MenuItemType(enum.Enum):
    """Menu item type."""

    SEPARATOR = "separator"
    SUB_MENU = "submenu"
    COMMAND = "command"
    RECENT_FILES = "recent_files"
    PLUGINS = "plugins"
    THEMES = "themes"


@dataclass
class MenuItem:
    """Menu item in GUI."""

    type: MenuItemType
    label: Optional[str] = None
    cmdline: Optional[str] = None
    children: Optional[list["MenuItem"]] = None


def _get_node(token: str) -> MenuItem:
    if token == "-":
        return MenuItem(type=MenuItemType.SEPARATOR)

    label: Optional[str]
    if "|" in token:
        label, artifact = token.split("|", 2)
    else:
        label = None
        artifact = token

    if artifact == "!recent!":
        return MenuItem(type=MenuItemType.RECENT_FILES, label=label)

    if artifact == "!plugins!":
        return MenuItem(type=MenuItemType.PLUGINS, label=label)

    if artifact == "!themes!":
        return MenuItem(type=MenuItemType.THEMES, label=label)

    if "|" in token:
        return MenuItem(
            type=MenuItemType.COMMAND, label=label, cmdline=artifact
        )

    return MenuItem(type=MenuItemType.SUB_MENU, label=artifact, children=[])


def _recurse_tree(
    parent: MenuItem, parent_depth: int, source: list[str]
) -> None:
    while source:
        last_line = source[0].rstrip()
        if not last_line:
            break

        match = re.search("^ *", last_line)
        assert match
        current_depth = len(match.group(0))
        if current_depth <= parent_depth:
            break

        token = last_line.strip()
        if current_depth <= parent_depth:
            continue

        source.pop(0)
        node = _get_node(token)
        if node.type == MenuItemType.SUB_MENU:
            _recurse_tree(node, current_depth, source)
        parent.children = parent.children or []
        parent.children.append(node)


class MenuConfig(SubConfig):
    """Configuration for GUI menu."""

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__()
        self._menu: dict[MenuContext, MenuItem] = {}
        self.load(None)

    def create_example_file(self, root_dir: Path) -> None:
        """Create an example file for the user to get to know the config
        syntax.

        :param root_dir: directory where to put the config file
        """
        user_path = _get_user_path(root_dir)
        if not user_path.exists():
            user_path.write_text((DATA_DIR / "menu.example").read_text())

    def load(self, root_dir: Optional[Path]) -> None:
        """Load internals of this config from the specified directory.

        :param root_dir: directory where to look for the matching config file
        """
        for context in MenuContext:
            self._menu[context] = MenuItem(
                type=MenuItemType.SUB_MENU, children=[]
            )

        self._loads((DATA_DIR / "menu.conf").read_text())

        if root_dir:
            user_path = _get_user_path(root_dir)
            if user_path.exists():
                try:
                    self._loads(user_path.read_text())
                except ConfigError as ex:
                    raise ConfigError(f"error loading {user_path}: {ex}")

    def _loads(self, text: str) -> None:
        sections: dict[MenuContext, str] = {}
        cur_context = MenuContext.MAIN_MENU
        lines = text.split("\n")
        while lines:
            line = lines.pop(0).rstrip()
            if not line or line.startswith("#"):
                continue

            match = re.match(r"^\[(.*)\]$", line)
            if match:
                try:
                    cur_context = MenuContext(match.group(1))
                except ValueError:
                    raise ConfigError(
                        f'"{match.group(1)}" is not a valid menu context'
                    )
                continue

            if cur_context not in sections:
                sections[cur_context] = ""
            sections[cur_context] += line + "\n"

        for context, section_text in sections.items():
            source = section_text.split("\n")
            _recurse_tree(self._menu[context], -1, source)

    def __getitem__(self, context: MenuContext) -> MenuItem:
        """Retrieve list of menu items by the specified context.

        :param context: context
        :return: contextual menu
        """
        return self._menu[context]

    def __iter__(
        self,
    ) -> Iterator[tuple[MenuContext, MenuItem]]:
        """Let users iterate directly over this config.

        :return: iterator
        """
        return ((context, items) for context, items in self._menu.items())


# convenience classes for plugins.


class MenuCommand(MenuItem):
    """Backwards-compatible class for creating menu commands."""

    def __init__(self, name: str, cmdline: str) -> None:
        """Initialize self.

        :param name: menu label
        :param cmdline: command line to run
        """
        super().__init__(
            type=MenuItemType.COMMAND, label=name, cmdline=cmdline
        )


class MenuSeparator(MenuItem):
    """Backwards-compatible class for creating menu separators."""

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__(type=MenuItemType.SEPARATOR)


class SubMenu(MenuItem):
    """Backwards-compatible class for creating submenus."""

    def __init__(
        self, name: str, children: Optional[list[MenuItem]] = None
    ) -> None:
        """Initialize self.

        :param name: menu label
        :param children: optional children menu items
        """
        super().__init__(
            type=MenuItemType.SUB_MENU, label=name, children=children or []
        )
