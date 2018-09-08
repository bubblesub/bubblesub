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
import json
import typing as T

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

    def __init__(self, name: str, *invocations: T.Iterable[str]) -> None:
        """
        Initialize self.

        Menu label is taken from the associated command.

        :param name: menu label
        :param invocations: invocations to execute
        """
        self.name = name
        self.invocations = invocations


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


_DEFAULT_MAIN_MENU: T.MutableSequence[MenuItem] = [
    SubMenu('&File', [
        MenuCommand('&New', '/new'),
        MenuCommand('&Open', '/open'),
        MenuCommand('&Save', '/save'),
        MenuCommand('&Save as', '/save-as'),
        MenuSeparator(),
        MenuCommand('&Load video', '/load-video'),
        MenuCommand('&Properties...', '/file-properties'),
        MenuSeparator(),
        MenuCommand('&Quit', '/quit'),
    ]),

    SubMenu('&Edit', [
        MenuCommand('&Undo', '/undo'),
        MenuCommand('&Redo', '/redo'),
        MenuSeparator(),
        MenuCommand('&Find...', '/search'),
        MenuCommand('&Find and replace...', '/search-and-replace'),
        MenuCommand('&Find previous', '/search-repeat -d=below'),
        MenuCommand('&Find next', '/search-repeat -d=above'),
        MenuSeparator(),
        MenuCommand('&Insert subtitle above', '/sub-insert --before'),
        MenuCommand('&Insert subtitle below', '/sub-insert --after'),
        MenuCommand('&Move selected subtitles above', '/edit/move-subs -d=above'),
        MenuCommand('&Move selected subtitles below', '/edit/move-subs -d=below'),
        MenuCommand('&Move selected subtitles to...', '/edit/move-subs-to'),
        MenuCommand('&Duplicate selected subtitles', '/sub-clone'),
        MenuCommand('&Delete selected subtitles', '/sub-delete'),
        MenuSeparator(),
        MenuCommand('&Swap selected subtitles notes with text', '/sub-set --note={text} --text={note}'),
        MenuCommand('&Split selected subtitles at current video frame', '/sub-split -p=cur-frame'),
        MenuCommand('&Join selected subtitles (keep first)', '/edit/join-subs-keep-first'),
        MenuCommand('&Join selected subtitles (concatenate)', '/edit/join-subs-concatenate'),
        MenuCommand('&Join selected subtitles (as karaoke)', '/edit/join-subs-as-karaoke'),
        MenuCommand('&Join selected subtitles (as transformation)', '/edit/join-subs-as-transformation'),
        MenuCommand('Split selected subtitles as karaoke', '/edit/split-sub-by-karaoke'),
        MenuSeparator(),
        MenuCommand('&Copy selected subtitles to clipboard', '/sub-copy'),
        MenuCommand('&Copy selected subtitles times to clipboard', '/sub-copy -s=times'),
        MenuCommand('&Copy selected subtitles text to clipboard', '/sub-copy -s=text'),
        MenuCommand('&Paste subtitles from clipboard above', '/sub-paste --before'),
        MenuCommand('&Paste subtitles from clipboard below', '/sub-paste --after'),
        MenuCommand('&Paste text from clipboard into selected subtitles', '/sub-paste-into -s=times'),
        MenuCommand('&Paste times from clipboard into selected subtitles', '/sub-paste-into -s=text'),
        MenuSeparator(),
        MenuCommand('&Check spelling...', '/spell-check'),
        MenuCommand('&Manage styles...', '/style-manager'),
    ]),

    SubMenu('Select', [
        MenuCommand('&Jump to subtitle (by number)...', '/sub-select ask-number'),
        MenuCommand('&Jump to subtitle (by time)...', '/sub-select ask-time'),
        MenuSeparator(),
        MenuCommand('&Select all', '/sub-select all'),
        MenuCommand('&Select previous subtitle', '/sub-select one-above'),
        MenuCommand('&Select next subtitle', '/sub-select one-below'),
        MenuCommand('&Select none', '/sub-select none'),
    ]),

    SubMenu('&View', [
        MenuCommand('&Switch to light color theme', '/set-palette light'),
        MenuCommand('&Switch to dark color theme', '/set-palette dark'),
        MenuSeparator(),
        MenuCommand('&Create audio sample', '/grid/create-audio-sample'),
        MenuCommand('&Save screenshot (without subtitles)', '/video/screenshot'),
        MenuCommand('&Save screenshot (with subtitles)', '/video/screenshot -i'),
        MenuSeparator(),
        MenuCommand('&Focus text editor', '/focus-widget text-editor -s'),
        MenuCommand('&Focus note editor', '/focus-widget note-editor -s'),
        MenuCommand('&Focus subtitles grid', '/focus-widget subtitles-grid'),
        MenuCommand('&Focus spectrogram', '/focus-widget spectrogram'),
        MenuCommand('&Focus console prompt', '/focus-widget console-input -s'),
        MenuCommand('&Focus console window', '/focus-widget console'),
    ]),

    SubMenu('&Playback', [
        SubMenu('Play around spectrogram selection', [
            MenuCommand('Play 0.5 second before spectrogram selection start', '/play-audio-sel -ds=-500ms --start'),
            MenuCommand('Play 0.5 second after spectrogram selection start', '/play-audio-sel -de=+500ms --start'),
            MenuCommand('Play 0.5 second before spectrogram selection end', '/play-audio-sel -ds=-500ms --end'),
            MenuCommand('Play 0.5 second after spectrogram selection end', '/play-audio-sel -de=+500ms --end'),
        ]),
        MenuCommand('&Play spectrogram selection', '/play-audio-sel'),
        MenuCommand('&Play selected subtitle', '/play-sub'),
        MenuCommand('&Play until end of file', '/pause off'),
        MenuSeparator(),
        MenuCommand('&Seek to...', '/seek -d=ask'),
        MenuCommand('&Seek 1 frame behind', '/seek -d=-1f'),
        MenuCommand('&Seek 1 frame ahead', '/seek -d=+1f'),
        MenuCommand('&Seek 10 frames behind', '/seek -d=-10f'),
        MenuCommand('&Seek 10 frames ahead', '/seek -d=+10f'),
        MenuSeparator(),
        MenuCommand('&Reset volume to 100%', '/set-volume 100'),
        MenuCommand('&Increase volume by 5%', '/set-volume {}-5'),
        MenuCommand('&Decrease volume by 5%', '/set-volume {}+5'),
        MenuCommand('&Mute', '/mute on'),
        MenuCommand('&Unmute', '/mute off'),
        MenuCommand('&Toggle mute', '/mute toggle'),
        MenuSeparator(),
        MenuCommand('&Pause', '/pause on'),
        MenuCommand('&Toggle pause', '/pause toggle'),
        MenuSeparator(),
        MenuCommand('&Speed up playback speed by 50%', '/set-playback-speed {}/1.5'),
        MenuCommand('&Slow down playback speed by 50%', '/set-playback-speed {}*1.5'),
    ]),

    SubMenu('&Timing', [
        SubMenu('Snap to nearest subtitle', [
            MenuCommand('Snap spectrogram selection start to previous subtitle start', '/audio-shift-sel -d=prev-sub-end --start'),
            MenuCommand('Snap spectrogram selection end to next subtitle end', '/audio-shift-sel -d=next-sub-start --end'),
            MenuCommand('Snap selected subtitles start to previous subtitle end', '/sub-shift -d=prev-sub-end --start'),
            MenuCommand('Snap selected subtitles end to next subtitle start', '/sub-shift -d=next-sub-start --end'),
        ]),

        SubMenu('Snap to nearest keyframe', [
            MenuCommand('Snap spectrogram selection start to previous keyframe', '/audio-shift-sel -d=-1kf --start'),
            MenuCommand('Snap spectrogram selection end to next keyframe', '/audio-shift-sel -d=+1kf --end'),
            MenuCommand('Snap selected subtitles start to previous keyframe', '/sub-shift -d=-1kf --start'),
            MenuCommand('Snap selected subtitles end to next keyframe', '/sub-shift -d=+1kf --end'),
        ]),

        SubMenu('Snap to current video frame', [
            MenuCommand('Snap spectrogram selection start to current video frame', '/audio-shift-sel -d=cur-frame --start'),
            MenuCommand('Snap spectrogram selection end to current video frame', '/audio-shift-sel -d=cur-frame --end'),
            MenuCommand('Place spectrogram selection at current video frame', '/audio-shift-sel -d=cur-frame --both', '/audio-shift-sel -d=default-sub-duration --end'),
            MenuCommand('Snap selected subtitles start to current video frame', '/sub-shift -d=cur-frame --start'),
            MenuCommand('Snap selected subtitles end to current video frame', '/sub-shift -d=cur-frame --end'),
            MenuCommand('Place selected subtitles at current video frame', '/sub-shift -d=cur-frame --both', '/sub-shift -d=default-sub-duration --end'),
        ]),

        SubMenu('Shift', [
            MenuCommand('Shift spectrogram selection start 10 frames back', '/audio-shift-sel -d=-10f --start'),
            MenuCommand('Shift spectrogram selection start 10 frames ahead', '/audio-shift-sel -d=+10f --start'),
            MenuCommand('Shift spectrogram selection end 10 frames back', '/audio-shift-sel -d=-10f --end'),
            MenuCommand('Shift spectrogram selection end 10 frames ahead', '/audio-shift-sel -d=+10f --end'),
            MenuCommand('Shift spectrogram selection start 1 frame back', '/audio-shift-sel -d=-1f --start'),
            MenuCommand('Shift spectrogram selection start 1 frame ahead', '/audio-shift-sel -d=+1f --start'),
            MenuCommand('Shift spectrogram selection end 1 frame back', '/audio-shift-sel -d=-1f --end'),
            MenuCommand('Shift spectrogram selection end 1 frame ahead', '/audio-shift-sel -d=+1f --end'),
            MenuCommand('Shift selected subtitles start 1 second back', '/sub-shift -d=-1000ms --start'),
            MenuCommand('Shift selected subtitles start 1 second ahead', '/sub-shift -d=+1000ms --start'),
            MenuCommand('Shift selected subtitles end 1 second back', '/sub-shift -d=-1000ms --end'),
            MenuCommand('Shift selected subtitles end 1 second ahead', '/sub-shift -d=+1000ms --end'),
        ]),

        MenuCommand('&Commit spectrogram selection', '/audio-commit-sel'),
        MenuSeparator(),
        MenuCommand('&Shift selected subtitles...', '/sub-shift --gui --no-align'),
        MenuSeparator(),
        MenuCommand(
            '&Scroll spectrogram forward by 5%',
            '/audio-scroll -d=-0.05'
        ),
        MenuCommand(
            '&Scroll spectrogram backward by 5%',
            '/audio-scroll -d=0.05'
        ),
        MenuCommand('&Zoom spectrogram in by 10%', '/audio-zoom -d=1.1'),
        MenuCommand('&Zoom spectrogram out by 10%', '/audio-zoom -d=0.9')
    ])
]

_DEFAULT_SUBTITLES_GRID_MENU = [
    MenuCommand('&Create audio sample', '/grid/create-audio-sample'),
    MenuSeparator(),
    MenuCommand('&Insert subtitle above', '/sub-insert --before'),
    MenuCommand('&Insert subtitle below', '/sub-insert --after'),
    MenuSeparator(),
    MenuCommand('&Copy to clipboard', '/sub-copy'),
    MenuCommand('&Paste from clipboard above', '/sub-paste --before'),
    MenuCommand('&Paste from clipboard below', '/sub-paste --after'),
    MenuSeparator(),
    MenuCommand('&Duplicate', '/sub-clone'),
    MenuCommand('&Split at current video frame','/sub-split -p=cur-frame'),
    MenuCommand('&Split as karaoke', '/edit/split-sub-by-karaoke'),
    MenuSeparator(),
    MenuCommand('&Join (keep first)', '/edit/join-subs-keep-first'),
    MenuCommand('&Join (concatenate)', '/edit/join-subs-concatenate'),
    MenuCommand('&Join (as karaoke)', '/edit/join-subs-as-karaoke'),
    MenuCommand('&Join (as transformation)', '/edit/join-subs-as-transformation'),
    MenuSeparator(),
    MenuCommand('&Snap to previous subtitle', '/sub-shift -d=prev-sub-end --start'),
    MenuCommand('&Snap to next subtitle', '/sub-shift -d=next-sub-start --end'),
    MenuSeparator(),
    MenuCommand('&Delete', '/sub-delete')
]


class MenuConfig(BaseConfig):
    """Configuration for GUI menu."""

    file_name = 'menu.json'

    def __init__(self) -> None:
        """Initialize self."""
        self._menu: T.Dict[MenuContext, T.MutableSequence[MenuItem]] = {
            MenuContext.MainMenu: _DEFAULT_MAIN_MENU,
            MenuContext.SubtitlesGrid: _DEFAULT_SUBTITLES_GRID_MENU,
        }

    def loads(self, text: str) -> None:
        """
        Load internals from a human readable representation.

        :param text: JSON
        """
        def load_menu(
                target: T.MutableSequence[MenuItem],
                source: T.Any
        ) -> None:
            if source is None:
                return

            target.clear()
            for item in source:
                if item['type'] == 'command':
                    target.append(
                        MenuCommand(item['name'], *item['invocations'])
                    )
                elif item['type'] == 'separator':
                    target.append(MenuSeparator())
                elif item['type'] == 'submenu':
                    sub_menu = SubMenu(item['name'], [])
                    load_menu(sub_menu.children, item['children'])
                    target.append(sub_menu)
                else:
                    raise ValueError(
                        'unknown menu type "{}"'.format(item['type'])
                    )

        obj = json.loads(text)
        for context in MenuContext:
            load_menu(self._menu[context], obj.get(context.value, None))

    def dumps(self) -> str:
        """
        Serialize internals to a human readable representation.

        :return: JSON
        """
        class MenuEncoder(json.JSONEncoder):
            def default(self, o: T.Any) -> T.Any:  # pylint: disable=E0202
                if isinstance(o, MenuSeparator):
                    return {'type': 'separator'}

                if isinstance(o, MenuCommand):
                    return {
                        'type': 'command',
                        'name': o.name,
                        'invocations': o.invocations
                    }

                if isinstance(o, SubMenu):
                    return {
                        'type': 'submenu',
                        'name': o.name,
                        'children': o.children
                    }

                return super().default(o)

        return json.dumps(
            {
                context.value: self._menu[context]
                for context in MenuContext
            },
            cls=MenuEncoder,
            indent=4
        )

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
