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

import json
import typing as T

from bubblesub.opt.base import BaseConfig


class Hotkey:
    """Hotkey definition."""

    def __init__(
            self,
            shortcut: str,
            command_name: str,
            *command_args: T.Any
    ) -> None:
        """
        Initialize self.

        :param shortcut: key combination that activates the hotkey
        :param command_name: name of the command to execute when the hotkey
            is invoked
        :param command_args: arguments for the command
        """
        self.shortcut = shortcut
        self.command_name = command_name
        self.command_args = list(command_args)


class HotkeysConfig(BaseConfig):
    """Configuration for global and widget-centric GUI hotkeys."""

    file_name = 'hotkeys.json'

    def __init__(self) -> None:
        """Initialize self."""
        self.hotkeys: T.Dict[str, T.List[Hotkey]] = {
            'global':
            [
                Hotkey('Ctrl+Shift+N', 'file/new'),
                Hotkey('Ctrl+O', 'file/open'),
                Hotkey('Ctrl+S', 'file/save'),
                Hotkey('Ctrl+Shift+S', 'file/save-as'),
                Hotkey('Ctrl+Q', 'file/quit'),
                Hotkey('Ctrl+G', 'grid/jump-to-line'),
                Hotkey('Ctrl+Shift+G', 'grid/jump-to-time'),
                Hotkey('Alt+G', 'video/seek-with-gui'),
                Hotkey('Ctrl+K', 'grid/select-prev-sub'),
                Hotkey('Ctrl+J', 'grid/select-next-sub'),
                Hotkey('Ctrl+A', 'grid/select-all'),
                Hotkey('Ctrl+Shift+A', 'grid/select-nothing'),
                Hotkey('Alt+1', 'video/play-around-sel-start', -500, 0),
                Hotkey('Alt+2', 'video/play-around-sel-start', 0, 500),
                Hotkey('Alt+3', 'video/play-around-sel-end', -500, 0),
                Hotkey('Alt+4', 'video/play-around-sel-end', 0, 500),
                Hotkey('Ctrl+R', 'video/play-around-sel', 0, 0),
                Hotkey('Ctrl+,', 'video/step-frame', -1),
                Hotkey('Ctrl+.', 'video/step-frame', 1),
                Hotkey('Ctrl+Shift+,', 'video/step-ms', -500, False),
                Hotkey('Ctrl+Shift+.', 'video/step-ms', 500, False),
                Hotkey('Ctrl+T', 'video/play-current-line'),
                Hotkey('Ctrl+P', 'video/toggle-pause'),
                Hotkey('Ctrl+Z', 'edit/undo'),
                Hotkey('Ctrl+Y', 'edit/redo'),
                Hotkey('Ctrl+F', 'edit/search'),
                Hotkey('Ctrl+H', 'edit/search-and-replace'),
                Hotkey('Alt+C', 'grid/copy-text-to-clipboard'),
                Hotkey('Ctrl+Return', 'edit/insert-below'),
                Hotkey('Ctrl+Delete', 'edit/delete'),
                Hotkey('Ctrl+Shift+1', 'audio/shift-sel-start', -10),
                Hotkey('Ctrl+Shift+2', 'audio/shift-sel-start', 10),
                Hotkey('Ctrl+Shift+3', 'audio/shift-sel-end', -10),
                Hotkey('Ctrl+Shift+4', 'audio/shift-sel-end', 10),
                Hotkey('Ctrl+1', 'audio/shift-sel-start', -1),
                Hotkey('Ctrl+2', 'audio/shift-sel-start', 1),
                Hotkey('Ctrl+3', 'audio/shift-sel-end', -1),
                Hotkey('Ctrl+4', 'audio/shift-sel-end', 1),
                Hotkey('Ctrl+B', 'audio/snap-sel-start-to-video'),
                Hotkey('Ctrl+N', 'audio/place-sel-at-video'),
                Hotkey('Ctrl+M', 'audio/snap-sel-end-to-video'),
                Hotkey('Ctrl+[', 'video/set-playback-speed', '{}/1.5'),
                Hotkey('Ctrl+]', 'video/set-playback-speed', '{}*1.5'),
                Hotkey('F3', 'edit/search-repeat', 1),
                Hotkey('Shift+F3', 'edit/search-repeat', -1),
                Hotkey('Alt+A', 'view/focus-spectrogram'),
                Hotkey('Alt+S', 'view/focus-grid'),
                Hotkey('Alt+D', 'view/focus-text-editor'),
                Hotkey('Alt+Shift+D', 'view/focus-note-editor'),
                Hotkey('Alt+X', 'edit/split-sub-at-video'),
                Hotkey('Alt+J', 'edit/join-subs/concatenate'),
                Hotkey('Alt+Up', 'edit/move-up'),
                Hotkey('Alt+Down', 'edit/move-down'),
            ],

            'spectrogram':
            [
                Hotkey('Shift+1', 'audio/shift-sel-start', -10),
                Hotkey('Shift+2', 'audio/shift-sel-start', 10),
                Hotkey('Shift+3', 'audio/shift-sel-end', -10),
                Hotkey('Shift+4', 'audio/shift-sel-end', 10),
                Hotkey('1', 'audio/shift-sel-start', -1),
                Hotkey('2', 'audio/shift-sel-start', 1),
                Hotkey('3', 'audio/shift-sel-end', -1),
                Hotkey('4', 'audio/shift-sel-end', 1),
                Hotkey('C', 'audio/commit-sel'),
                Hotkey('K', 'edit/insert-above'),
                Hotkey('J', 'edit/insert-below'),
                Hotkey('R', 'video/play-around-sel', 0, 0),
                Hotkey('T', 'video/play-current-line'),
                Hotkey('P', 'video/toggle-pause'),
                Hotkey('Shift+K', 'grid/select-prev-sub'),
                Hotkey('Shift+J', 'grid/select-next-sub'),
                Hotkey('A', 'audio/scroll', -0.05),
                Hotkey('F', 'audio/scroll', 0.05),
                Hotkey('Ctrl+-', 'audio/zoom', 1.1),
                Hotkey('Ctrl+=', 'audio/zoom', 0.9),
                Hotkey('Ctrl++', 'audio/zoom', 0.9),
                Hotkey(',', 'video/step-frame', -1),
                Hotkey('.', 'video/step-frame', 1),
                Hotkey('Ctrl+Shift+,', 'video/step-ms', -1500, False),
                Hotkey('Ctrl+Shift+.', 'video/step-ms', 1500, False),
                Hotkey('Shift+,', 'video/step-ms', -500, False),
                Hotkey('Shift+.', 'video/step-ms', 500, False),
                Hotkey('B', 'audio/snap-sel-start-to-video'),
                Hotkey('N', 'audio/place-sel-at-video'),
                Hotkey('M', 'audio/snap-sel-end-to-video'),
                Hotkey('[', 'video/set-playback-speed', '{}/1.5'),
                Hotkey(']', 'video/set-playback-speed', '{}*1.5'),
                Hotkey('Alt+Left', 'audio/snap-sel-start-to-prev-sub'),
                Hotkey('Alt+Right', 'audio/snap-sel-end-to-next-sub'),
            ],
        }

    def loads(self, text: str) -> None:
        """
        Load internals from a human readable representation.

        :param text: JSON
        """
        obj = json.loads(text)
        for context_name in self.hotkeys:
            self.hotkeys[context_name].clear()
            for hotkey_obj in obj.get(context_name, []):
                self.hotkeys[context_name].append(
                    Hotkey(
                        hotkey_obj['shortcut'],
                        hotkey_obj['command_name'],
                        *hotkey_obj['command_args']
                    )
                )

    def dumps(self) -> str:
        """
        Serialize internals to a human readable representation.

        :return: JSON
        """
        return json.dumps(
            {
                context_name:
                [
                    {
                        'shortcut': hotkey.shortcut,
                        'command_name': hotkey.command_name,
                        'command_args': hotkey.command_args,
                    }
                    for hotkey in hotkeys
                ]
                for context_name, hotkeys in self.__iter__()
            },
            indent=4
        )

    def __iter__(self) -> T.Iterator[T.Tuple[str, T.List[Hotkey]]]:
        """
        Let users iterate directly over this config.

        :return: iterator
        """
        return iter(self.hotkeys.items())
