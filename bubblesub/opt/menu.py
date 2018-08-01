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

    def __init__(self, invocation: str) -> None:
        """
        Initialize self.

        Menu label is taken from the associated command.

        :param invocation: invocation to execute
        """
        self.invocation = invocation


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
                    MenuCommand('/new'),
                    MenuCommand('/open'),
                    MenuCommand('/save'),
                    MenuCommand('/save-as'),
                    MenuSeparator(),
                    MenuCommand('/load-video'),
                    MenuCommand('/file-properties'),
                    MenuSeparator(),
                    MenuCommand('/quit'),
                ]),

                SubMenu('&Edit', [
                    MenuCommand('/undo'),
                    MenuCommand('/redo'),
                    MenuSeparator(),
                    MenuCommand('/search'),
                    MenuCommand('/search-and-replace'),
                    MenuCommand('/search-repeat -d below'),
                    MenuCommand('/search-repeat -d above'),
                    MenuSeparator(),
                    MenuCommand('/edit/insert-sub -d above'),
                    MenuCommand('/edit/insert-sub -d below'),
                    MenuCommand('/edit/move-subs -d above'),
                    MenuCommand('/edit/move-subs -d below'),
                    MenuCommand('/edit/move-subs-to'),
                    MenuCommand('/edit/duplicate-subs'),
                    MenuCommand('/edit/delete-subs'),
                    MenuSeparator(),
                    MenuCommand('/edit/swap-subs-text-and-notes'),
                    MenuCommand('/edit/split-sub-at-current-video-frame'),
                    MenuCommand('/edit/join-subs-keep-first'),
                    MenuCommand('/edit/join-subs-concatenate'),
                    MenuCommand('/edit/join-subs-as-karaoke'),
                    MenuCommand('/edit/join-subs-as-transformation'),
                    MenuCommand('/edit/split-sub-by-karaoke'),
                    MenuSeparator(),
                    MenuCommand('/copy-subs'),
                    MenuCommand('/copy-subs -s times'),
                    MenuCommand('/copy-subs -s text'),
                    MenuCommand('/paste-subs -t selected --before'),
                    MenuCommand('/paste-subs -t selected --after'),
                    MenuCommand('/paste-into-subs -t selected -s times'),
                    MenuCommand('/paste-into-subs -t selected -s text'),
                    MenuSeparator(),
                    MenuCommand('/spell-check'),
                    MenuCommand('/style-manager'),
                ]),

                SubMenu('Select', [
                    MenuCommand('/grid/jump-to-sub-by-number'),
                    MenuCommand('/grid/jump-to-sub-by-time'),
                    MenuSeparator(),
                    MenuCommand('/select-subs all'),
                    MenuCommand('/select-subs one-above'),
                    MenuCommand('/select-subs one-below'),
                    MenuCommand('/select-subs none'),
                ]),

                SubMenu('&View', [
                    MenuCommand('/set-palette light'),
                    MenuCommand('/set-palette dark'),
                    MenuSeparator(),
                    MenuCommand('/grid/create-audio-sample'),
                    MenuCommand('/video/screenshot'),
                    MenuCommand('/video/screenshot -i'),
                    MenuSeparator(),
                    MenuCommand('/focus-widget text-editor -s'),
                    MenuCommand('/focus-widget note-editor -s'),
                    MenuCommand('/focus-widget subtitles-grid'),
                    MenuCommand('/focus-widget spectrogram'),
                    MenuCommand('/focus-widget console-input -s'),
                    MenuCommand('/focus-widget console'),
                ]),

                SubMenu('&Playback', [
                    SubMenu('Play around selection', [
                        MenuCommand(
                            '/video/play-around-sel -t start -ds -500'
                        ),
                        MenuCommand('/video/play-around-sel -t start -de 500'),
                        MenuCommand('/video/play-around-sel -t end -ds -500'),
                        MenuCommand('/video/play-around-sel -t end -de 500'),
                    ]),
                    MenuCommand('/video/play-around-sel'),
                    MenuCommand('/video/play-current-sub'),
                    MenuCommand('/video/pause disable'),
                    MenuSeparator(),
                    MenuCommand('/video/seek-with-gui'),
                    MenuCommand('/video/step-frame -d -1'),
                    MenuCommand('/video/step-frame -d 1'),
                    MenuCommand('/video/step-frame -d -10'),
                    MenuCommand('/video/step-frame -d 10'),
                    MenuSeparator(),
                    MenuCommand('/video/set-volume 100'),
                    MenuCommand('/video/set-volume {}-5'),
                    MenuCommand('/video/set-volume {}+5'),
                    MenuCommand('/video/mute on'),
                    MenuCommand('/video/mute off'),
                    MenuCommand('/video/mute toggle'),
                    MenuSeparator(),
                    MenuCommand('/video/pause on'),
                    MenuCommand('/video/pause toggle'),
                    MenuSeparator(),
                    MenuCommand('/video/set-playback-speed {}/1.5'),
                    MenuCommand('/video/set-playback-speed {}*1.5'),
                ]),

                SubMenu('&Timing', [
                    SubMenu('Snap to nearest subtitle', [
                        MenuCommand(
                            '/audio/snap-sel-to-near-sub -t start -d above'
                        ),
                        MenuCommand(
                            '/audio/snap-sel-to-near-sub -t end -d below'
                        ),
                        MenuCommand(
                            '/edit/snap-subs-to-near-sub -t start -d above'
                        ),
                        MenuCommand(
                            '/edit/snap-subs-to-near-sub -t end -d below'
                        ),
                    ]),

                    SubMenu('Snap to nearest keyframe', [
                        MenuCommand(
                            '/audio/snap-sel-to-near-keyframe '
                            '-t start -d above'
                        ),
                        MenuCommand(
                            '/audio/snap-sel-to-near-keyframe -t end -d below'
                        ),
                    ]),

                    SubMenu('Snap to current video frame', [
                        MenuCommand(
                            '/audio/snap-sel-to-current-video-frame -t start'
                        ),
                        MenuCommand(
                            '/audio/snap-sel-to-current-video-frame -t end'
                        ),
                        MenuCommand('/audio/place-sel-at-current-video-frame'),
                        MenuCommand(
                            '/edit/snap-subs-to-current-video-frame -t start'
                        ),
                        MenuCommand(
                            '/edit/snap-subs-to-current-video-frame -t end'
                        ),
                        MenuCommand('/edit/place-subs-at-current-video-frame'),
                    ]),

                    SubMenu('Shift', [
                        MenuCommand('/audio/shift-sel -f -t start -d -10'),
                        MenuCommand('/audio/shift-sel -f -t start -d 10'),
                        MenuCommand('/audio/shift-sel -f -t end -d -10'),
                        MenuCommand('/audio/shift-sel -f -t end -d 10'),
                        MenuCommand('/audio/shift-sel -f -t start -d -1'),
                        MenuCommand('/audio/shift-sel -f -t start -d 1'),
                        MenuCommand('/audio/shift-sel -f -t end -d -1'),
                        MenuCommand('/audio/shift-sel -f -t end -d 1'),
                        MenuCommand('/edit/shift-subs -t start -d -1000'),
                        MenuCommand('/edit/shift-subs -t start -d 1000'),
                        MenuCommand('/edit/shift-subs -t end -d -1000'),
                        MenuCommand('/edit/shift-subs -t end -d 1000'),
                    ]),

                    MenuCommand('/audio/commit-sel'),
                    MenuSeparator(),
                    MenuCommand('/edit/shift-subs-with-gui'),
                    MenuSeparator(),
                    MenuCommand('/audio/scroll-spectrogram -d -0.05'),
                    MenuCommand('/audio/scroll-spectrogram -d 0.05'),
                    MenuCommand('/audio/zoom-spectrogram -d 1.1'),
                    MenuCommand('/audio/zoom-spectrogram -d 0.9')
                ])
            ],

            MenuContext.SubtitlesGrid:
            [
                MenuCommand('/grid/create-audio-sample'),
                MenuSeparator(),
                MenuCommand('/edit/insert-sub -d above'),
                MenuCommand('/edit/insert-sub -d below'),
                MenuSeparator(),
                MenuCommand('/copy-subs'),
                MenuCommand('/paste-subs -t selected --before'),
                MenuCommand('/paste-subs -t selected --after'),
                MenuSeparator(),
                MenuCommand('/edit/duplicate-subs'),
                MenuCommand('/edit/split-sub-at-current-video-frame'),
                MenuCommand('/edit/split-sub-by-karaoke'),
                MenuSeparator(),
                MenuCommand('/edit/join-subs-keep-first'),
                MenuCommand('/edit/join-subs-concatenate'),
                MenuCommand('/edit/join-subs-as-karaoke'),
                MenuCommand('/edit/join-subs-as-transformation'),
                MenuSeparator(),
                MenuCommand('/edit/snap-subs-to-near-sub -t start -d above'),
                MenuCommand('/edit/snap-subs-to-near-sub -t end -d below'),
                MenuSeparator(),
                MenuCommand('/edit/delete-subs')
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
                    target.append(MenuCommand(item['invocation']))
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
                        'invocation': o.invocation
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
