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
import json
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
            *invocations: T.Iterable[str],
    ) -> None:
        """
        Initialize self.

        :param shortcut: key combination that activates the hotkey
        :param invocations: invocations to execute
        """
        self.shortcut = shortcut
        self.invocations = invocations


class HotkeysConfig(BaseConfig):
    """Configuration for global and widget-centric GUI hotkeys."""

    file_name = 'hotkeys.json'

    def __init__(self) -> None:
        """Initialize self."""
        self.hotkeys: T.Dict[HotkeyContext, T.List[Hotkey]] = {
            HotkeyContext.Global: [],
            HotkeyContext.Spectrogram: [],
            HotkeyContext.SubtitlesGrid: [],
        }
        self.loads((ROOT_DIR / 'hotkeys.json').read_text())

    def loads(self, text: str) -> None:
        """
        Load internals from a human readable representation.

        :param text: JSON
        """
        obj = json.loads(text)
        for context in self.hotkeys:
            self.hotkeys[context].clear()
            for hotkey_obj in obj.get(context.value, []):
                self.hotkeys[context].append(
                    Hotkey(
                        hotkey_obj['shortcut'],
                        *hotkey_obj['invocations']
                    )
                )

    def dumps(self) -> str:
        """
        Serialize internals to a human readable representation.

        :return: JSON
        """
        return json.dumps(
            {
                context.value:
                [
                    {
                        'shortcut': hotkey.shortcut,
                        'invocations': hotkey.invocations,
                    }
                    for hotkey in hotkeys
                ]
                for context, hotkeys in self.__iter__()
            },
            indent=4
        )

    def __iter__(self) -> T.Iterator[T.Tuple[HotkeyContext, T.List[Hotkey]]]:
        """
        Let users iterate directly over this config.

        :return: iterator
        """
        return iter(self.hotkeys.items())
