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
import typing as T
from pathlib import Path

from bubblesub.cfg.base import ConfigError, SubConfig
from bubblesub.data import ROOT_DIR


def _get_user_path(root_dir: Path) -> Path:
    return root_dir / "menu.conf"


class MenuContext(enum.Enum):
    """Which GUI widget the menu appears in."""

    MainMenu = "main"
    SubtitlesGrid = "subtitles_grid"


class MenuItem:
    """Base menu item in GUI."""


class MenuCommand(MenuItem):
    """Menu item associated with a bubblesub command."""

    def __init__(self, name: str, cmdline: str) -> None:
        """
        Initialize self.

        Menu label is taken from the associated command.

        :param name: menu label
        :param cmdline: command line to execute
        """
        self.name = name
        self.cmdline = cmdline


class MenuSeparator(MenuItem):
    """Empty horizontal line."""


class MenuPlaceholder(MenuItem):
    """Menu text that does nothing (always disabled)."""

    def __init__(self, text: str) -> None:
        """
        Initialize self.

        :param text: text to display
        """
        self.text = text


class SubMenu(MenuItem):
    """Menu item that opens up another sub menu."""

    def __init__(
        self, name: str, children: T.MutableSequence[MenuItem]
    ) -> None:
        """
        Initialize self.

        :param name: menu label
        :param children: submenu items
        """
        self.name = name
        self.children = children


class MenuConfig(SubConfig):
    """Configuration for GUI menu."""

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__()
        self._menu: T.Dict[MenuContext, T.MutableSequence[MenuItem]] = {
            context: [] for context in MenuContext
        }
        self.load(None)

    def create_example_file(self, root_dir: Path) -> None:
        """
        Create an example file for the user to get to know the config syntax.

        :param root_dir: directory where to put the config file
        """
        user_path = _get_user_path(root_dir)
        if not user_path.exists():
            user_path.write_text((ROOT_DIR / "menu.example").read_text())

    def load(self, root_dir: T.Optional[Path]) -> None:
        """
        Load internals of this config from the specified directory.

        :param root_dir: directory where to look for the matching config file
        """
        for context in MenuContext:
            self._menu[context].clear()
        self._loads((ROOT_DIR / "menu.conf").read_text())
        if root_dir:
            user_path = _get_user_path(root_dir)
            if user_path.exists():
                try:
                    self._loads(user_path.read_text())
                except ConfigError as ex:
                    raise ConfigError(f"error loading {user_path}: {ex}")

    def _loads(self, text: str) -> None:
        sections: T.Dict[MenuContext, str] = {}
        cur_context = MenuContext.MainMenu
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

        def _recurse_tree(
            parent: T.MutableSequence[MenuItem],
            parent_depth: int,
            source: T.List[str],
        ) -> None:
            while source:
                last_line = source[0].rstrip()
                if not last_line:
                    break

                current_depth = len(re.search("^ *", last_line).group(0))
                if current_depth <= parent_depth:
                    break

                token = last_line.strip()
                if current_depth > parent_depth:
                    source.pop(0)
                    if token == "-":
                        parent.append(MenuSeparator())
                    elif "|" not in token:
                        node = SubMenu(name=token, children=[])
                        parent.append(node)
                        _recurse_tree(node.children, current_depth, source)
                    else:
                        name, cmdline = token.split("|", 1)
                        parent.append(MenuCommand(name=name, cmdline=cmdline))

        for context, section_text in sections.items():
            source = section_text.split("\n")
            _recurse_tree(self._menu[context], -1, source)

    def __getitem__(self, context: MenuContext) -> T.MutableSequence[MenuItem]:
        """
        Retrieve list of menu items by the specified context.

        :param context: context
        :return: contextual menu
        """
        return self._menu[context]

    def __iter__(
        self
    ) -> T.Iterator[T.Tuple[MenuContext, T.MutableSequence[MenuItem]]]:
        """
        Let users iterate directly over this config.

        :return: iterator
        """
        return ((context, items) for context, items in self._menu.items())
