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
            invocation: str,
    ) -> None:
        """
        Initialize self.

        :param shortcut: key combination that activates the hotkey
        :param invocation: invocation to execute
        """
        self.shortcut = shortcut
        self.invocation = invocation


class HotkeysConfig(BaseConfig):
    """Configuration for global and widget-centric GUI hotkeys."""

    file_name = 'hotkeys.json'

    def __init__(self) -> None:
        """Initialize self."""
        self.hotkeys: T.Dict[HotkeyContext, T.List[Hotkey]] = {
            HotkeyContext.Global:
            [
                Hotkey('Ctrl+Shift+N', '/new'),
                Hotkey('Ctrl+O', '/open'),
                Hotkey('Ctrl+S', '/save'),
                Hotkey('Ctrl+Shift+S', '/save-as'),
                Hotkey('Ctrl+Q', '/quit'),
                Hotkey('Ctrl+G', '/select-subs ask-number'),
                Hotkey('Ctrl+Shift+G', '/select-subs ask-time'),
                Hotkey('Alt+G', '/video/seek-with-gui'),
                Hotkey('Ctrl+K', '/select-subs one-above'),
                Hotkey('Ctrl+J', '/select-subs one-below'),
                Hotkey('Ctrl+A', '/select-subs all'),
                Hotkey('Ctrl+Shift+A', '/select-subs none'),
                Hotkey('Alt+2', '/video/play-around-sel -t start -de 500'),
                Hotkey('Alt+1', '/video/play-around-sel -t start -ds -500'),
                Hotkey('Alt+3', '/video/play-around-sel -t end -ds -500'),
                Hotkey('Alt+4', '/video/play-around-sel -t end -de 500'),
                Hotkey('Ctrl+R', '/video/play-around-sel'),
                Hotkey('Ctrl+,', '/video/step-frame -d -1'),
                Hotkey('Ctrl+.', '/video/step-frame -d 1'),
                Hotkey('Ctrl+Shift+,', '/video/step-ms -d -500'),
                Hotkey('Ctrl+Shift+.', '/video/step-ms -d 500'),
                Hotkey('Ctrl+T', '/video/play-current-sub'),
                Hotkey('Ctrl+P', '/video/pause toggle'),
                Hotkey('Ctrl+Z', '/undo'),
                Hotkey('Ctrl+Y', '/redo'),
                Hotkey('Ctrl+F', '/search'),
                Hotkey('Ctrl+H', '/search-and-replace'),
                Hotkey('Ctrl+Return', '/edit/insert-sub -d below'),
                Hotkey('Ctrl+Delete', '/edit/delete-subs'),
                Hotkey('Ctrl+Shift+1', '/audio/shift-sel -f -t start -d 10'),
                Hotkey('Ctrl+Shift+2', '/audio/shift-sel -f -t start -d 10'),
                Hotkey('Ctrl+Shift+3', '/audio/shift-sel -f -t end -d -10'),
                Hotkey('Ctrl+Shift+4', '/audio/shift-sel -f -t end -d 10'),
                Hotkey('Ctrl+1', '/audio/shift-sel -f -t start -d -1'),
                Hotkey('Ctrl+2', '/audio/shift-sel -f -t start -d 1'),
                Hotkey('Ctrl+3', '/audio/shift-sel -f -t end -d -1'),
                Hotkey('Ctrl+4', '/audio/shift-sel -f -t end -d 1'),
                Hotkey(
                    'Ctrl+B', '/audio/snap-sel-to-current-video-frame -t start'
                ),
                Hotkey(
                    'Ctrl+M', '/audio/snap-sel-to-current-video-frame -t end'
                ),
                Hotkey('Ctrl+N', '/audio/place-sel-at-current-video-frame'),
                Hotkey('Ctrl+[', '/video/set-playback-speed {}/1.5'),
                Hotkey('Ctrl+]', '/video/set-playback-speed {}*1.5'),
                Hotkey('F3', '/search-repeat -d below'),
                Hotkey('Shift+F3', '/search-repeat -d above'),
                Hotkey('Alt+A', '/focus-widget spectrogram'),
                Hotkey('Alt+S', '/focus-widget subtitles-grid'),
                Hotkey('Alt+D', '/focus-widget text-editor -s'),
                Hotkey('Alt+Shift+D', '/focus-widget note-editor -s'),
                Hotkey('Alt+C', '/focus-widget console-input -s'),
                Hotkey('Alt+Shift+C', '/focus-widget console'),
                Hotkey('Alt+X', '/edit/split-sub-at-current-video-frame'),
                Hotkey('Alt+J', '/edit/join-subs-concatenate'),
                Hotkey('Alt+Up', '/edit/move-subs -d above'),
                Hotkey('Alt+Down', '/edit/move-subs -d below'),
                Hotkey('Alt+Return', '/file-properties'),
            ],

            HotkeyContext.Spectrogram:
            [
                Hotkey('Shift+1', '/audio/shift-sel -f -t start -d -10'),
                Hotkey('Shift+2', '/audio/shift-sel -f -t start -d 10'),
                Hotkey('Shift+3', '/audio/shift-sel -f -t end -d -10'),
                Hotkey('Shift+4', '/audio/shift-sel -f -t end -d 10'),
                Hotkey('1', '/audio/shift-sel -f -t start -d -1'),
                Hotkey('2', '/audio/shift-sel -f -t start -d 1'),
                Hotkey('3', '/audio/shift-sel -f -t end -d -1'),
                Hotkey('4', '/audio/shift-sel -f -t end -d 1'),
                Hotkey('C', '/spectrogram-commit-sel'),
                Hotkey('K', '/edit/insert-sub -d above'),
                Hotkey('J', '/edit/insert-sub -d below'),
                Hotkey('R', '/video/play-around-sel'),
                Hotkey('T', '/video/play-current-sub'),
                Hotkey('P', '/video/pause toggle'),
                Hotkey('Shift+K', '/select-subs one-above'),
                Hotkey('Shift+J', '/select-subs one-below'),
                Hotkey('A', '/audio/scroll-spectrogram -d -0.05'),
                Hotkey('F', '/audio/scroll-spectrogram -d 0.05'),
                Hotkey('Ctrl+-', '/audio/zoom-spectrogram -d 1.1'),
                Hotkey('Ctrl+=', '/audio/zoom-spectrogram -d 0.9'),
                Hotkey('Ctrl++', '/audio/zoom-spectrogram -d 0.9'),
                Hotkey(',', '/video/step-frame -d -1'),
                Hotkey('.', '/video/step-frame -d 1'),
                Hotkey('Ctrl+Shift+,', '/video/step-ms -d -1500'),
                Hotkey('Ctrl+Shift+.', '/video/step-ms -d 1500'),
                Hotkey('Shift+,', '/video/step-ms -d -500'),
                Hotkey('Shift+.', '/video/step-ms -d 500'),
                Hotkey('B', '/audio/snap-sel-to-current-video-frame -t start'),
                Hotkey('M', '/audio/snap-sel-to-current-video-frame -t end'),
                Hotkey('N', '/audio/place-sel-at-current-video-frame'),
                Hotkey('[', '/video/set-playback-speed {}/1.5'),
                Hotkey(']', '/video/set-playback-speed {}*1.5'),
                Hotkey(
                    'Alt+Left', '/audio/snap-sel-to-near-sub -t start -d above'
                ),
                Hotkey(
                    'Alt+Right', '/audio/snap-sel-to-near-sub -t end -d below'
                ),
                Hotkey(
                    'Alt+Shift+Left',
                    '/audio/snap-sel-to-near-keyframe -t start -d above'
                ),
                Hotkey(
                    'Alt+Shift+Right',
                    '/audio/snap-sel-to-near-keyframe -t end -d below'
                ),
            ],

            HotkeyContext.SubtitlesGrid:
            [
                Hotkey('Ctrl+C', '/copy-subs'),
                Hotkey('Ctrl+V', '/paste-subs -t selected --after'),
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
                        hotkey_obj['invocation']
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
                        'invocation': hotkey.invocation,
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
