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
import itertools
import re
import typing as T

from bubblesub.data import ROOT_DIR
from bubblesub.opt.base import BaseConfig


class MenuContext(enum.Enum):
    """Which GUI widget the menu appears in."""

    MainMenu = 'main'
    SubtitlesGrid = 'subtitles_grid'


class MenuItem:
    """Base menu item in GUI."""

    pass


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

    pass


class SubMenu(MenuItem):
    """Menu item that opens up another sub menu."""

    def __init__(
            self,
            name: str,
            children: T.MutableSequence[MenuItem]
    ) -> None:
        """
        Initialize self.

        :param name: menu label
        :param children: submenu items
        """
        self.name = name
        self.children = children


class MenuConfig(BaseConfig):
    """Configuration for GUI menu."""

    file_name = 'menu.conf'

    def __init__(self) -> None:
        """Initialize self."""
        self._menu: T.Dict[MenuContext, T.MutableSequence[MenuItem]] = {
            MenuContext.MainMenu: [],
            MenuContext.SubtitlesGrid: [],
        }
        self.loads((ROOT_DIR / self.file_name).read_text())

    def loads(self, text: str) -> None:
        """
        Load internals from a human readable representation.

        :param text: source text
        """

        sections: T.Dict[MenuContext, str] = {}
        cur_context = MenuContext.MainMenu
        lines = text.split('\n')
        while lines:
            line = lines.pop(0).rstrip()
            if not line or line.startswith('#'):
                continue

            match = re.match(r'\[(\w+)\]', line)
            if match:
                cur_context = MenuContext(match.group(1))
                continue
            if cur_context not in sections:
                sections[cur_context] = ''
            sections[cur_context] += line + '\n'

        def _recurse_tree(
                parent: T.List[MenuItem], depth: int, source: T.List[str]
        ) -> None:
            while source:
                last_line = source[0].rstrip()
                if not last_line:
                    break

                tabs = last_line.count(' ')
                if tabs < depth:
                    break

                token = last_line.strip()
                if tabs >= depth:
                    source.pop(0)
                    if token == "-":
                        parent.append(MenuSeparator())
                    elif "|" not in token:
                        node = SubMenu(name=token, children=[])
                        parent.append(node)
                        _recurse_tree(
                            node.children, tabs + 1, source
                        )
                    else:
                        name, cmdline = token.split("|", 1)
                        parent.append(MenuCommand(name=name, cmdline=cmdline))

        for context, section_text in sections.items():
            source = section_text.split('\n')
            self._menu[context] = []
            _recurse_tree(self._menu[context], 0, source)

    def dumps(self) -> str:
        """
        Serialize internals to a human readable representation.

        :return: resulting text
        """
        def _recurse_tree(source: T.List[MenuItem]) -> T.Iterable[str]:
            for item in source:
                if isinstance(item, MenuSeparator):
                    yield "-"
                elif isinstance(item, MenuCommand):
                    yield f"{item.name}|{item.cmdline}"
                elif isinstance(item, SubMenu):
                    yield from (
                        [item.name] +
                        [
                            " " * 4 + subitem
                            for subitem in _recurse_tree(item.children)
                        ]
                    )
                else:
                    raise AssertionError

        lines: T.List[str] = []
        for context, source in self._menu.items():
            if source:
                lines.append(f"[{context.value}]")
                lines += list(_recurse_tree(source))
                lines.append("")

        while not lines[-1]:
            lines.pop()

        return "\n".join(lines)

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
