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
        self.hotkeys: T.Dict[HotkeyContext, T.List[Hotkey]] = {
            HotkeyContext.Global:
            [
                Hotkey('Ctrl+Shift+N', 'file/new'),
                Hotkey('Ctrl+O', 'file/open'),
                Hotkey('Ctrl+S', 'file/save'),
                Hotkey('Ctrl+Shift+S', 'file/save-as'),
                Hotkey('Ctrl+Q', 'file/quit'),
                Hotkey('Ctrl+G', 'grid/jump-to-sub-by-number'),
                Hotkey('Ctrl+Shift+G', 'grid/jump-to-sub-by-time'),
                Hotkey('Alt+G', 'video/seek-with-gui'),
                Hotkey('Ctrl+K', 'grid/select-near-sub', 'above'),
                Hotkey('Ctrl+J', 'grid/select-near-sub', 'below'),
                Hotkey('Ctrl+A', 'grid/select-all-subs'),
                Hotkey('Ctrl+Shift+A', 'grid/clear-sub-sel'),
                Hotkey('Alt+2', 'video/play-around-sel', 'start', 0, 500),
                Hotkey('Alt+1', 'video/play-around-sel', 'start', -500, 0),
                Hotkey('Alt+3', 'video/play-around-sel', 'end', -500, 0),
                Hotkey('Alt+4', 'video/play-around-sel', 'end', 0, 500),
                Hotkey('Ctrl+R', 'video/play-around-sel', 'both', 0, 0),
                Hotkey('Ctrl+,', 'video/step-frame', -1),
                Hotkey('Ctrl+.', 'video/step-frame', 1),
                Hotkey('Ctrl+Shift+,', 'video/step-ms', -500, False),
                Hotkey('Ctrl+Shift+.', 'video/step-ms', 500, False),
                Hotkey('Ctrl+T', 'video/play-current-sub'),
                Hotkey('Ctrl+P', 'video/pause', 'toggle'),
                Hotkey('Ctrl+Z', 'edit/undo'),
                Hotkey('Ctrl+Y', 'edit/redo'),
                Hotkey('Ctrl+F', 'edit/search'),
                Hotkey('Ctrl+H', 'edit/search-and-replace'),
                Hotkey('Ctrl+Return', 'edit/insert-sub', 'below'),
                Hotkey('Ctrl+Delete', 'edit/delete-subs'),
                Hotkey('Ctrl+Shift+1', 'audio/shift-sel', 'start', -10),
                Hotkey('Ctrl+Shift+2', 'audio/shift-sel', 'start', 10),
                Hotkey('Ctrl+Shift+3', 'audio/shift-sel', 'end', -10),
                Hotkey('Ctrl+Shift+4', 'audio/shift-sel', 'end', 10),
                Hotkey('Ctrl+1', 'audio/shift-sel', 'start', -1),
                Hotkey('Ctrl+2', 'audio/shift-sel', 'start', 1),
                Hotkey('Ctrl+3', 'audio/shift-sel', 'end', -1),
                Hotkey('Ctrl+4', 'audio/shift-sel', 'end', 1),
                Hotkey(
                    'Ctrl+B', 'audio/snap-sel-to-current-video-frame', 'start'
                ),
                Hotkey(
                    'Ctrl+M', 'audio/snap-sel-to-current-video-frame', 'end'
                ),
                Hotkey('Ctrl+N', 'audio/place-sel-at-current-video-frame'),
                Hotkey('Ctrl+[', 'video/set-playback-speed', '{}/1.5'),
                Hotkey('Ctrl+]', 'video/set-playback-speed', '{}*1.5'),
                Hotkey('F3', 'edit/search-repeat', 1),
                Hotkey('Shift+F3', 'edit/search-repeat', -1),
                Hotkey('Alt+A', 'view/focus-spectrogram'),
                Hotkey('Alt+S', 'view/focus-subs-grid'),
                Hotkey('Alt+D', 'view/focus-text-editor'),
                Hotkey('Alt+Shift+D', 'view/focus-note-editor'),
                Hotkey('Alt+X', 'edit/split-sub-at-current-video-frame'),
                Hotkey('Alt+J', 'edit/join-subs-concatenate'),
                Hotkey('Alt+Up', 'edit/move-subs', 'above'),
                Hotkey('Alt+Down', 'edit/move-subs', 'below'),
                Hotkey('Alt+Return', 'file/properties'),
            ],

            HotkeyContext.Spectrogram:
            [
                Hotkey('Shift+1', 'audio/shift-sel', 'start', -10),
                Hotkey('Shift+2', 'audio/shift-sel', 'start', 10),
                Hotkey('Shift+3', 'audio/shift-sel', 'end', -10),
                Hotkey('Shift+4', 'audio/shift-sel', 'end', 10),
                Hotkey('1', 'audio/shift-sel', 'start', -1),
                Hotkey('2', 'audio/shift-sel', 'start', 1),
                Hotkey('3', 'audio/shift-sel', 'end', -1),
                Hotkey('4', 'audio/shift-sel', 'end', 1),
                Hotkey('C', 'audio/commit-sel'),
                Hotkey('K', 'edit/insert-sub', 'above'),
                Hotkey('J', 'edit/insert-sub', 'below'),
                Hotkey('R', 'video/play-around-sel', 'both', 0, 0),
                Hotkey('T', 'video/play-current-sub'),
                Hotkey('P', 'video/pause', 'toggle'),
                Hotkey('Shift+K', 'grid/select-near-sub', 'above'),
                Hotkey('Shift+J', 'grid/select-near-sub', 'below'),
                Hotkey('A', 'audio/scroll-spectrogram', -0.05),
                Hotkey('F', 'audio/scroll-spectrogram', 0.05),
                Hotkey('Ctrl+-', 'audio/zoom-spectrogram', 1.1),
                Hotkey('Ctrl+=', 'audio/zoom-spectrogram', 0.9),
                Hotkey('Ctrl++', 'audio/zoom-spectrogram', 0.9),
                Hotkey(',', 'video/step-frame', -1),
                Hotkey('.', 'video/step-frame', 1),
                Hotkey('Ctrl+Shift+,', 'video/step-ms', -1500, False),
                Hotkey('Ctrl+Shift+.', 'video/step-ms', 1500, False),
                Hotkey('Shift+,', 'video/step-ms', -500, False),
                Hotkey('Shift+.', 'video/step-ms', 500, False),
                Hotkey('B', 'audio/snap-sel-to-current-video-frame', 'start'),
                Hotkey('M', 'audio/snap-sel-to-current-video-frame', 'end'),
                Hotkey('N', 'audio/place-sel-at-current-video-frame'),
                Hotkey('[', 'video/set-playback-speed', '{}/1.5'),
                Hotkey(']', 'video/set-playback-speed', '{}*1.5'),
                Hotkey(
                    'Alt+Left', 'audio/snap-sel-to-near-sub', 'start', 'above'
                ),
                Hotkey(
                    'Alt+Right', 'audio/snap-sel-to-near-sub', 'end', 'below'
                ),
                Hotkey(
                    'Alt+Shift+Left', 'audio/snap-sel-to-near-keyframe',
                    'start', 'above'
                ),
                Hotkey(
                    'Alt+Shift+Right', 'audio/snap-sel-to-near-keyframe',
                    'end', 'below'
                ),
            ],

            HotkeyContext.SubtitlesGrid:
            [
                Hotkey('Ctrl+C', 'grid/copy-subs'),
                Hotkey('Ctrl+V', 'grid/paste-subs', 'below'),
            ],
        }

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
                context.value:
                [
                    {
                        'shortcut': hotkey.shortcut,
                        'command_name': hotkey.command_name,
                        'command_args': hotkey.command_args,
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
