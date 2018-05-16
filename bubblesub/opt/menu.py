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

    def __init__(self, command_name: str, *command_args: T.Any) -> None:
        """
        Initialize self.

        Menu label is taken from the associated command.

        :param command_name: name of the command to execute when the menu item
            is invoked
        :param command_args: arguments for the command
        """
        self.command_name = command_name
        self.command_args = list(command_args)


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

    file_name = 'menu.json'

    def __init__(self) -> None:
        """Initialize self."""
        self._menu: T.Dict[MenuContext, T.MutableSequence[MenuItem]] = {
            MenuContext.MainMenu:
            [
                SubMenu('&File', [
                    MenuCommand('file/new'),
                    MenuCommand('file/open'),
                    MenuCommand('file/save'),
                    MenuCommand('file/save-as'),
                    MenuSeparator(),
                    MenuCommand('file/load-video'),
                    MenuCommand('file/properties'),
                    MenuSeparator(),
                    MenuCommand('file/quit'),
                ]),

                SubMenu('&Edit', [
                    MenuCommand('edit/undo'),
                    MenuCommand('edit/redo'),
                    MenuSeparator(),
                    MenuCommand('edit/search'),
                    MenuCommand('edit/search-and-replace'),
                    MenuCommand('edit/search-repeat', 1),
                    MenuCommand('edit/search-repeat', -1),
                    MenuSeparator(),
                    MenuCommand('edit/insert-sub', 'above'),
                    MenuCommand('edit/insert-sub', 'below'),
                    MenuCommand('edit/move-subs', 'above'),
                    MenuCommand('edit/move-subs', 'below'),
                    MenuCommand('edit/move-subs-to'),
                    MenuCommand('edit/duplicate-subs'),
                    MenuCommand('edit/delete-subs'),
                    MenuSeparator(),
                    MenuCommand('edit/swap-subs-text-and-notes'),
                    MenuCommand('edit/split-sub-at-current-video-frame'),
                    MenuCommand('edit/join-subs-keep-first'),
                    MenuCommand('edit/join-subs-concatenate'),
                    MenuCommand('edit/join-subs-as-karaoke'),
                    MenuCommand('edit/join-subs-as-transformation'),
                    MenuCommand('edit/split-sub-by-karaoke'),
                    MenuSeparator(),
                    MenuCommand('grid/copy-subs'),
                    MenuCommand('grid/paste-subs', 'above'),
                    MenuCommand('grid/paste-subs', 'below'),
                    MenuSeparator(),
                    MenuCommand('edit/spell-check'),
                    MenuCommand('edit/manage-styles'),
                ]),

                SubMenu('Select', [
                    MenuCommand('grid/jump-to-sub-by-number'),
                    MenuCommand('grid/jump-to-sub-by-time'),
                    MenuSeparator(),
                    MenuCommand('grid/select-all-subs'),
                    MenuCommand('grid/select-near-sub', 'above'),
                    MenuCommand('grid/select-near-sub', 'below'),
                    MenuCommand('grid/clear-sub-sel'),
                ]),

                SubMenu('&View', [
                    MenuCommand('view/set-palette', 'light'),
                    MenuCommand('view/set-palette', 'dark'),
                    MenuSeparator(),
                    MenuCommand('grid/create-audio-sample'),
                    MenuCommand('video/screenshot', False),
                    MenuCommand('video/screenshot', True),
                    MenuSeparator(),
                    MenuCommand('view/focus-text-editor'),
                    MenuCommand('view/focus-note-editor'),
                    MenuCommand('view/focus-subs-grid'),
                    MenuCommand('view/focus-spectrogram'),
                ]),

                SubMenu('&Playback', [
                    SubMenu('Play around selection', [
                        MenuCommand('video/play-around-sel', 'start', -500, 0),
                        MenuCommand('video/play-around-sel', 'start', 0, 500),
                        MenuCommand('video/play-around-sel', 'end', -500, 0),
                        MenuCommand('video/play-around-sel', 'end', 0, 500),
                    ]),
                    MenuCommand('video/play-around-sel', 'both', 0, 0),
                    MenuCommand('video/play-current-sub'),
                    MenuCommand('video/unpause'),
                    MenuSeparator(),
                    MenuCommand('video/seek-with-gui'),
                    MenuCommand('video/step-frame', -1),
                    MenuCommand('video/step-frame', 1),
                    MenuCommand('video/step-frame', -10),
                    MenuCommand('video/step-frame', 10),
                    MenuSeparator(),
                    MenuCommand('video/set-volume', '100'),
                    MenuCommand('video/set-volume', '{}-5'),
                    MenuCommand('video/set-volume', '{}+5'),
                    MenuSeparator(),
                    MenuCommand('video/pause'),
                    MenuCommand('video/toggle-pause'),
                    MenuSeparator(),
                    MenuCommand('video/set-playback-speed', '{}/1.5'),
                    MenuCommand('video/set-playback-speed', '{}*1.5'),
                ]),

                SubMenu('&Timing', [
                    SubMenu('Snap to nearest subtitle', [
                        MenuCommand(
                            'audio/snap-sel-to-near-sub', 'start', 'above'
                        ),
                        MenuCommand(
                            'audio/snap-sel-to-near-sub', 'end', 'below'
                        ),
                        MenuCommand(
                            'edit/snap-subs-to-near-sub', 'start', 'above'
                        ),
                        MenuCommand(
                            'edit/snap-subs-to-near-sub', 'end', 'below'
                        ),
                    ]),

                    SubMenu('Snap to nearest keyframe', [
                        MenuCommand(
                            'audio/snap-sel-to-near-keyframe', 'start', 'above'
                        ),
                        MenuCommand(
                            'audio/snap-sel-to-near-keyframe', 'end', 'below'
                        ),
                    ]),

                    SubMenu('Snap to current video frame', [
                        MenuCommand(
                            'audio/snap-sel-to-current-video-frame', 'start'
                        ),
                        MenuCommand(
                            'audio/snap-sel-to-current-video-frame', 'end'
                        ),
                        MenuCommand('audio/place-sel-at-current-video-frame'),
                        MenuCommand(
                            'edit/snap-subs-to-current-video-frame', 'start'
                        ),
                        MenuCommand(
                            'edit/snap-subs-to-current-video-frame', 'end'
                        ),
                        MenuCommand('edit/place-subs-at-current-video-frame'),
                    ]),

                    SubMenu('Shift', [
                        MenuCommand('audio/shift-sel', 'start', -10),
                        MenuCommand('audio/shift-sel', 'start', 10),
                        MenuCommand('audio/shift-sel', 'end', -10),
                        MenuCommand('audio/shift-sel', 'end', 10),
                        MenuCommand('audio/shift-sel', 'start', -1),
                        MenuCommand('audio/shift-sel', 'start', 1),
                        MenuCommand('audio/shift-sel', 'end', -1),
                        MenuCommand('audio/shift-sel', 'end', 1),
                        MenuCommand('edit/shift-subs', 'start', -1000),
                        MenuCommand('edit/shift-subs', 'start', 1000),
                        MenuCommand('edit/shift-subs', 'end', -1000),
                        MenuCommand('edit/shift-subs', 'end', 1000),
                    ]),

                    MenuCommand('audio/commit-sel'),
                    MenuSeparator(),
                    MenuCommand('edit/shift-subs-with-gui'),
                    MenuSeparator(),
                    MenuCommand('audio/scroll-spectrogram', -0.05),
                    MenuCommand('audio/scroll-spectrogram', 0.05),
                    MenuCommand('audio/zoom-spectrogram', 1.1),
                    MenuCommand('audio/zoom-spectrogram', 0.9)
                ])
            ],

            MenuContext.SubtitlesGrid:
            [
                MenuCommand('grid/create-audio-sample'),
                MenuSeparator(),
                MenuCommand('edit/insert-sub', 'above'),
                MenuCommand('edit/insert-sub', 'below'),
                MenuSeparator(),
                MenuCommand('grid/copy-subs'),
                MenuCommand('grid/paste-subs', 'above'),
                MenuCommand('grid/paste-subs', 'below'),
                MenuSeparator(),
                MenuCommand('edit/duplicate-subs'),
                MenuCommand('edit/split-sub-at-current-video-frame'),
                MenuCommand('edit/split-sub-by-karaoke'),
                MenuSeparator(),
                MenuCommand('edit/join-subs-keep-first'),
                MenuCommand('edit/join-subs-concatenate'),
                MenuCommand('edit/join-subs-as-karaoke'),
                MenuCommand('edit/join-subs-as-transformation'),
                MenuSeparator(),
                MenuCommand('edit/snap-subs-to-near-sub', 'start', 'above'),
                MenuCommand('edit/snap-subs-to-near-sub', 'end', 'below'),
                MenuSeparator(),
                MenuCommand('edit/delete-subs')
            ]
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
                        MenuCommand(
                            item['command_name'],
                            *item['command_args']
                        )
                    )
                elif item['type'] == 'separator':
                    target.append(MenuSeparator())
                elif item['type'] == 'submenu':
                    sub_menu = SubMenu(item['name'], [])
                    load_menu(sub_menu.children, item['children'])
                    target.append(sub_menu)
                else:
                    raise ValueError(
                        'Unknown menu type "{}"'.format(item['type'])
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

                elif isinstance(o, MenuCommand):
                    return {
                        'type': 'command',
                        'command_name': o.command_name,
                        'command_args': o.command_args
                    }

                elif isinstance(o, SubMenu):
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
