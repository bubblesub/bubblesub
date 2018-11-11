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

"""Hotkey config."""

import enum
import re
import typing as T

from bubblesub.data import ROOT_DIR
from bubblesub.opt.base import BaseConfig


class HotkeyContext(enum.Enum):
    """Which GUI widget the hotkey works in."""

    Global = 'global'
    Spectrogram = 'spectrogram'
    SubtitlesGrid = 'subtitles_grid'


class Hotkey:
    """Hotkey definition."""

    def __init__(
            self,
            shortcut: str,
            *invocations: str,
    ) -> None:
        """
        Initialize self.

        :param shortcut: key combination that activates the hotkey
        :param invocations: invocations to execute
        """
        self.shortcut = shortcut
        self.invocations: T.Tuple[str, ...] = invocations


class HotkeysConfig(BaseConfig):
    """Configuration for global and widget-centric GUI hotkeys."""

    file_name = 'hotkeys.conf'

    def __init__(self) -> None:
        """Initialize self."""
        self.hotkeys: T.Dict[HotkeyContext, T.List[Hotkey]] = {
            context: [] for context in HotkeyContext
        }
        self.loads((ROOT_DIR / self.file_name).read_text())

    def loads(self, text: str) -> None:
        """
        Load internals from a human readable representation.

        :param text: source text
        """
        for context in HotkeyContext:
            self.hotkeys[context].clear()

        cur_context = HotkeyContext.Global
        for i, line in enumerate(text.split('\n'), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            match = re.match(r'\[(\w+)\]', line)
            if match:
                cur_context = HotkeyContext(match.group(1))
                continue

            try:
                shortcut, commands = re.split(r'\s+', line, maxsplit=1)
            except ValueError:
                raise ValueError(f'syntax error near line #{i} ({line})')
            # TODO: change command parsing
            commands = [command.strip() for command in commands.split(';')]
            self.hotkeys[cur_context].append(Hotkey(shortcut, *commands))

    def dumps(self) -> str:
        """
        Serialize internals to a human readable representation.

        :return: resulting text
        """
        lines: T.List[str] = []
        for context, hotkeys in self:
            if not hotkeys:
                continue

            lines.append(f'[{context.value}]')
            for hotkey in hotkeys:
                lines.append(
                    f'{hotkey.shortcut:20s} {";".join(hotkey.invocations)}'
                )
            lines.append('')

        while not lines[-1]:
            lines.pop()

        return '\n'.join(lines)

    def __iter__(self) -> T.Iterator[T.Tuple[HotkeyContext, T.List[Hotkey]]]:
        """
        Let users iterate directly over this config.

        :return: iterator
        """
        return iter(self.hotkeys.items())
