import json
import typing as T

from bubblesub.opt.base import BaseConfig


class MenuItem:
    pass


class MenuCommand(MenuItem):
    def __init__(self, command_name: str, *command_args: T.Any) -> None:
        self.command_name = command_name
        self.command_args = command_args


class MenuSeparator(MenuItem):
    pass


class SubMenu(MenuItem):
    def __init__(
            self,
            name: str,
            children: T.MutableSequence[MenuItem]
    ) -> None:
        self.name = name
        self.children = children


class MenuConfig(BaseConfig):
    file_name = 'menu.json'

    def __init__(self) -> None:
        self.main: T.MutableSequence[MenuItem] = [
            SubMenu(
                '&File',
                [
                    MenuCommand('file/new'),
                    MenuCommand('file/open'),
                    MenuCommand('file/save'),
                    MenuCommand('file/save-as'),
                    MenuSeparator(),
                    MenuCommand('file/load-video'),
                    MenuSeparator(),
                    MenuCommand('file/quit'),
                ]
            ),

            SubMenu(
                '&Edit',
                [
                    MenuCommand('edit/undo'),
                    MenuCommand('edit/redo'),
                    MenuSeparator(),
                    MenuCommand('grid/jump-to-line'),
                    MenuCommand('grid/jump-to-time'),
                    MenuCommand('grid/select-prev-sub'),
                    MenuCommand('grid/select-next-sub'),
                    MenuCommand('grid/select-all'),
                    MenuCommand('grid/select-nothing'),
                    MenuSeparator(),
                    MenuCommand('edit/search'),
                    MenuCommand('edit/search-and-replace'),
                    MenuCommand('edit/search-repeat', 1),
                    MenuCommand('edit/search-repeat', -1),
                    MenuSeparator(),
                    MenuCommand('edit/insert-above'),
                    MenuCommand('edit/insert-below'),
                    MenuCommand('edit/duplicate'),
                    MenuCommand('edit/delete'),
                    MenuCommand('edit/move-up'),
                    MenuCommand('edit/move-down'),
                    MenuCommand('edit/move-to'),
                    MenuSeparator(),
                    MenuCommand('edit/swap-text-and-notes'),
                    MenuCommand('edit/split-sub-at-video'),
                    MenuCommand('edit/karaoke-split'),
                    MenuCommand('edit/karaoke-join'),
                    MenuCommand('edit/transformation-join'),
                    MenuCommand('edit/join-subs/keep-first'),
                    MenuCommand('edit/join-subs/concatenate'),
                    MenuSeparator(),
                    MenuCommand('grid/copy-text-to-clipboard'),
                    MenuCommand('grid/copy-times-to-clipboard'),
                    MenuCommand('grid/paste-times-from-clipboard'),
                    MenuCommand('grid/copy-to-clipboard'),
                    MenuCommand('grid/paste-from-clipboard-above'),
                    MenuCommand('grid/paste-from-clipboard-below'),
                    MenuSeparator(),
                    MenuCommand('edit/spell-check'),
                    MenuCommand('edit/manage-styles'),
                ]
            ),

            SubMenu(
                '&View',
                [
                    MenuCommand('view/set-palette', 'light'),
                    MenuCommand('view/set-palette', 'dark'),
                    MenuSeparator(),
                    MenuCommand('grid/create-audio-sample'),
                    MenuCommand('video/screenshot', False),
                    MenuCommand('video/screenshot', True),
                    MenuSeparator(),
                    MenuCommand('view/focus-text-editor'),
                    MenuCommand('view/focus-note-editor'),
                    MenuCommand('view/focus-grid'),
                    MenuCommand('view/focus-spectrogram'),
                ]
            ),

            SubMenu(
                '&Playback',
                [
                    SubMenu(
                        'Play around selection',
                        [
                            MenuCommand(
                                'video/play-around-sel-start', -500, 0
                            ),
                            MenuCommand('video/play-around-sel-start', 0, 500),
                            MenuCommand('video/play-around-sel-end', -500, 0),
                            MenuCommand('video/play-around-sel-end', 0, 500),
                        ]
                    ),
                    MenuCommand('video/play-around-sel', 0, 0),
                    MenuCommand('video/play-current-line'),
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
                ]
            ),

            SubMenu(
                '&Timing',
                [
                    SubMenu(
                        'Snap selection to subtitles',
                        [
                            MenuCommand('audio/snap-sel-start-to-prev-sub'),
                            MenuCommand('audio/snap-sel-end-to-next-sub'),
                        ]
                    ),
                    SubMenu(
                        'Snap selection to video frame',
                        [
                            MenuCommand('audio/snap-sel-start-to-video'),
                            MenuCommand('audio/snap-sel-end-to-video'),
                            MenuCommand('audio/snap-sel-to-video'),
                        ]
                    ),
                    SubMenu(
                        'Shift selection',
                        [
                            MenuCommand('audio/shift-sel-start', -10),
                            MenuCommand('audio/shift-sel-start', 10),
                            MenuCommand('audio/shift-sel-end', -10),
                            MenuCommand('audio/shift-sel-end', 10),
                            MenuCommand('audio/shift-sel-start', -1),
                            MenuCommand('audio/shift-sel-start', 1),
                            MenuCommand('audio/shift-sel-end', -1),
                            MenuCommand('audio/shift-sel-end', 1),
                        ]
                    ),
                    MenuCommand('audio/commit-sel'),
                    MenuSeparator(),
                    MenuCommand('edit/shift-subs-with-gui'),
                    MenuSeparator(),
                    MenuCommand('audio/scroll', -1),
                    MenuCommand('audio/scroll', 1),
                    MenuCommand('audio/zoom', 1.1),
                    MenuCommand('audio/zoom', 0.9)
                ]
            )
        ]

        self.context: T.MutableSequence[MenuItem] = [
            MenuCommand('grid/create-audio-sample'),
            MenuSeparator(),
            MenuCommand('edit/insert-above'),
            MenuCommand('edit/insert-below'),
            MenuSeparator(),
            MenuCommand('edit/duplicate'),
            MenuCommand('edit/split-sub-at-video'),
            MenuSeparator(),
            MenuCommand('edit/join-subs/keep-first'),
            MenuCommand('edit/join-subs/concatenate'),
            MenuCommand('edit/karaoke-join'),
            MenuCommand('edit/transformation-join'),
            MenuSeparator(),
            MenuCommand('edit/karaoke-split'),
            MenuCommand('edit/snap-subs-start-to-prev-sub'),
            MenuCommand('edit/snap-subs-end-to-next-sub'),
            MenuSeparator(),
            MenuCommand('edit/delete')
        ]

    def loads(self, text: str) -> None:
        def load_menu(
                target: T.MutableSequence[MenuItem],
                source: T.Any
        ) -> None:
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
        load_menu(self.main, obj['main'])
        load_menu(self.context, obj['context'])

    def dumps(self) -> str:
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
                'main': self.main,
                'context': self.context
            },
            cls=MenuEncoder,
            indent=4
        )
