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

    def __init__(self, *invocations: T.Iterable[str]) -> None:
        """
        Initialize self.

        Menu label is taken from the associated command.

        :param invocations: invocations to execute
        """
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
        MenuCommand('/search-repeat -d=below'),
        MenuCommand('/search-repeat -d=above'),
        MenuSeparator(),
        MenuCommand('/edit/insert-sub -d=above'),
        MenuCommand('/edit/insert-sub -d=below'),
        MenuCommand('/edit/move-subs -d=above'),
        MenuCommand('/edit/move-subs -d=below'),
        MenuCommand('/edit/move-subs-to'),
        MenuCommand('/sub-clone'),
        MenuCommand('/sub-delete'),
        MenuSeparator(),
        MenuCommand('/edit/swap-subs-text-and-notes'),
        MenuCommand('/edit/split-sub-at-current-video-frame'),
        MenuCommand('/edit/join-subs-keep-first'),
        MenuCommand('/edit/join-subs-concatenate'),
        MenuCommand('/edit/join-subs-as-karaoke'),
        MenuCommand('/edit/join-subs-as-transformation'),
        MenuCommand('/edit/split-sub-by-karaoke'),
        MenuSeparator(),
        MenuCommand('/sub-copy'),
        MenuCommand('/sub-copy -s times'),
        MenuCommand('/sub-copy -s text'),
        MenuCommand('/sub-paste -t=selected --before'),
        MenuCommand('/sub-paste -t=selected --after'),
        MenuCommand('/sub-paste-into -t=selected -s times'),
        MenuCommand('/sub-paste-into -t=selected -s text'),
        MenuSeparator(),
        MenuCommand('/spell-check'),
        MenuCommand('/style-manager'),
    ]),

    SubMenu('Select', [
        MenuCommand('/sub-select ask-number'),
        MenuCommand('/sub-select ask-time'),
        MenuSeparator(),
        MenuCommand('/sub-select all'),
        MenuCommand('/sub-select one-above'),
        MenuCommand('/sub-select one-below'),
        MenuCommand('/sub-select none'),
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
            MenuCommand('/play-audio-sel -ds=-500ms --start'),
            MenuCommand('/play-audio-sel -de=+500ms --start'),
            MenuCommand('/play-audio-sel -ds=-500ms --end'),
            MenuCommand('/play-audio-sel -de=+500ms --end'),
        ]),
        MenuCommand('/play-audio-sel'),
        MenuCommand('/play-sub'),
        MenuCommand('/pause off'),
        MenuSeparator(),
        MenuCommand('/seek -d=ask'),
        MenuCommand('/seek -d=-1f'),
        MenuCommand('/seek -d=+1f'),
        MenuCommand('/seek -d=-10f'),
        MenuCommand('/seek -d=+10f'),
        MenuSeparator(),
        MenuCommand('/set-volume 100'),
        MenuCommand('/set-volume {}-5'),
        MenuCommand('/set-volume {}+5'),
        MenuCommand('/mute on'),
        MenuCommand('/mute off'),
        MenuCommand('/mute toggle'),
        MenuSeparator(),
        MenuCommand('/pause on'),
        MenuCommand('/pause toggle'),
        MenuSeparator(),
        MenuCommand('/set-playback-speed {}/1.5'),
        MenuCommand('/set-playback-speed {}*1.5'),
    ]),

    SubMenu('&Timing', [
        SubMenu('Snap to nearest subtitle', [
            MenuCommand('/audio-shift-sel -d=prev-sub-end --start'),
            MenuCommand('/audio-shift-sel -d=next-sub-start --end'),
            MenuCommand('/sub-shift -d=prev-sub-end --start'),
            MenuCommand('/sub-shift -d=next-sub-start --end'),
        ]),

        SubMenu('Snap to nearest keyframe', [
            MenuCommand('/audio-shift-sel -d=-1kf --start'),
            MenuCommand('/audio-shift-sel -d=+1kf --end'),
        ]),

        SubMenu('Snap to current video frame', [
            MenuCommand('/audio-shift-sel -d=cur-frame --start'),
            MenuCommand('/audio-shift-sel -d=cur-frame --end'),
            MenuCommand(
                '/audio-shift-sel -d=cur-frame --both',
                '/audio-shift-sel -d=default-sub-duration --end'
            ),
            MenuCommand('/sub-shift -d=cur-frame --start'),
            MenuCommand('/sub-shift -d=cur-frame --end'),
            MenuCommand(
                '/sub-shift -d=cur-frame --both',
                '/sub-shift -d=default-sub-duration --end'
            ),
        ]),

        SubMenu('Shift', [
            MenuCommand('/audio-shift-sel -d=-10f --start'),
            MenuCommand('/audio-shift-sel -d=+10f --start'),
            MenuCommand('/audio-shift-sel -d=-10f --end'),
            MenuCommand('/audio-shift-sel -d=+10f --end'),
            MenuCommand('/audio-shift-sel -d=-1f --start'),
            MenuCommand('/audio-shift-sel -d=+1f --start'),
            MenuCommand('/audio-shift-sel -d=-1f --end'),
            MenuCommand('/audio-shift-sel -d=+1f --end'),
            MenuCommand('/sub-shift -d=-1000ms --start'),
            MenuCommand('/sub-shift -d=+1000ms --start'),
            MenuCommand('/sub-shift -d=-1000ms --end'),
            MenuCommand('/sub-shift -d=+1000ms --end'),
        ]),

        MenuCommand('/audio-commit-sel'),
        MenuSeparator(),
        MenuCommand('/edit/shift-subs-with-gui'),
        MenuSeparator(),
        MenuCommand('/audio-scroll -d=-0.05'),
        MenuCommand('/audio-scroll -d=0.05'),
        MenuCommand('/audio-zoom -d=1.1'),
        MenuCommand('/audio-zoom -d=0.9')
    ])
]

_DEFAULT_SUBTITLES_GRID_MENU = [
    MenuCommand('/grid/create-audio-sample'),
    MenuSeparator(),
    MenuCommand('/edit/insert-sub -d=above'),
    MenuCommand('/edit/insert-sub -d=below'),
    MenuSeparator(),
    MenuCommand('/sub-copy'),
    MenuCommand('/sub-paste -t=selected --before'),
    MenuCommand('/sub-paste -t=selected --after'),
    MenuSeparator(),
    MenuCommand('/sub-clone'),
    MenuCommand('/edit/split-sub-at-current-video-frame'),
    MenuCommand('/edit/split-sub-by-karaoke'),
    MenuSeparator(),
    MenuCommand('/edit/join-subs-keep-first'),
    MenuCommand('/edit/join-subs-concatenate'),
    MenuCommand('/edit/join-subs-as-karaoke'),
    MenuCommand('/edit/join-subs-as-transformation'),
    MenuSeparator(),
    MenuCommand('/sub-shift -d=prev-sub-end --start'),
    MenuCommand('/sub-shift -d=next-sub-start --end'),
    MenuSeparator(),
    MenuCommand('/sub-delete')
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
                    target.append(MenuCommand(*item['invocations']))
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
