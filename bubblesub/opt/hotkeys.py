import json
import typing as T

from bubblesub.opt.base import BaseConfig


class Hotkey:
    def __init__(
            self,
            shortcut: str,
            command_name: str,
            *command_args: T.Any
    ) -> None:
        self.shortcut = shortcut
        self.command_name = command_name
        self.command_args = command_args


class HotkeysConfig(BaseConfig):
    file_name = 'hotkeys.json'

    def __init__(self) -> None:
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
                Hotkey('Ctrl+N', 'audio/snap-sel-to-video'),
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

            'audio':
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
                Hotkey('A', 'audio/scroll', -1),
                Hotkey('F', 'audio/scroll', 1),
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
                Hotkey('N', 'audio/snap-sel-to-video'),
                Hotkey('M', 'audio/snap-sel-end-to-video'),
                Hotkey('[', 'video/set-playback-speed', '{}/1.5'),
                Hotkey(']', 'video/set-playback-speed', '{}*1.5'),
                Hotkey('Alt+Left', 'audio/snap-sel-start-to-prev-sub'),
                Hotkey('Alt+Right', 'audio/snap-sel-end-to-next-sub'),
            ],
        }

    def loads(self, text: str) -> None:
        obj = json.loads(text)
        for context_name in self.hotkeys:
            self.hotkeys[context_name].clear()
            for hotkey_obj in obj[context_name]:
                self.hotkeys[context_name].append(
                    Hotkey(
                        hotkey_obj['shortcut'],
                        hotkey_obj['command_name'],
                        *hotkey_obj['command_args']
                    )
                )

    def dumps(self) -> str:
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
                for context_name, hotkeys in self
            },
            indent=4
        )

    def __iter__(self):
        return iter(self.hotkeys.items())
