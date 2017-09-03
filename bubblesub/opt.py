from pathlib import Path
import json
import xdg


_DEFAULT_GENERAL = {
    'convert_newlines': True,
    'fonts': {
        'editor': '',
        'notes': '',
    },
    'subs': {
        'max_characters_per_second': 15,
        'default_duration': 2000,
    },
    'video': {
        'subs_sync_interval': 65,
    },
    'audio': {
        'spectrogram_resolution': 10,
        'spectrogram_sync_interval': 65,
    },
    'grid': {
        'columns': [
            'start',
            'end',
            'style',
            'actor',
            'text',
            'note',
            'duration',
            'cps',
        ],
    },
    'search': {
        'history': [],
        'regex': False,
        'case_sensitive': False,
        'use_regexes': False,
        'mode': 1,
    },

    'current_palette': 'light',
    'palettes': {
        'dark': {
            'Window':                          (53, 53, 53),
            'Active+WindowText':               (255, 255, 255),
            'Inactive+WindowText':             (255, 255, 255),
            'Disabled+WindowText':             (100, 100, 100),
            'Base':                            (25, 25, 25),
            'AlternateBase':                   (53, 53, 53),
            'Active+Text':                     (255, 255, 255),
            'Inactive+Text':                   (255, 255, 255),
            'Disabled+Text':                   (100, 100, 100),
            'BrightText':                      (255, 255, 255),
            'Button':                          (53, 53, 53),
            'Active+ButtonText':               (255, 255, 255),
            'Inactive+ButtonText':             (255, 255, 255),
            'Disabled+ButtonText':             (100, 100, 100),
            'Link':                            (42, 130, 218),
            'Highlight':                       (42, 130, 218),
            'HighlightedText':                 (0, 0, 0),
            'ToolTipBase':                     (255, 255, 255),
            'ToolTipText':                     (255, 255, 255),
            'spectrogram/video-marker':        (0, 160, 0),
            'spectrogram/subtitle':            (42, 130, 218),
            'spectrogram/focused-selection':   (0xFF, 0xA0, 0x00),
            'spectrogram/unfocused-selection': (0xA0, 0xA0, 0x60),
            'grid/comment':                    (53, 53, 53),
        },

        'light': {
            'Window':                          (239, 235, 231),
            'Active+WindowText':               (0, 0, 0),
            'Inactive+WindowText':             (0, 0, 0),
            'Disabled+WindowText':             (190, 190, 190),
            'Active+Base':                     (255, 255, 255),
            'Inactive+Base':                   (255, 255, 255),
            'Disabled+Base':                   (239, 235, 231),
            'AlternateBase':                   (247, 245, 243),
            'Active+Text':                     (0, 0, 0),
            'Inactive+Text':                   (0, 0, 0),
            'Disabled+Text':                   (190, 190, 190),
            'BrightText':                      (255, 255, 255),
            'Button':                          (239, 235, 231),
            'Active+ButtonText':               (0, 0, 0),
            'Inactive+ButtonText':             (0, 0, 0),
            'Disabled+ButtonText':             (190, 190, 190),
            'Active+Highlight':                (48, 140, 198),
            'Inactive+Highlight':              (48, 140, 198),
            'Disabled+Highlight':              (145, 141, 126),
            'HighlightedText':                 (255, 255, 255),

            'Light':                           (255, 255, 255),
            'Midlight':                        (203, 199, 196),
            'Active+Dark':                     (159, 157, 154),
            'Inactive+Dark':                   (159, 157, 154),
            'Disabled+Dark':                   (190, 182, 174),
            'Mid':                             (184, 181, 178),
            'Active+Shadow':                   (118, 116, 114),
            'Inactive+Shadow':                 (118, 116, 114),
            'Disabled+Shadow':                 (177, 174, 171),

            'Link':                            (0, 0, 255),
            'LinkVisited':                     (255, 0, 255),
            'ToolTipBase':                     (255, 255, 220),
            'ToolTipText':                     (0, 0, 0),

            'spectrogram/video-marker':        (0, 160, 0),
            'spectrogram/subtitle':            (42, 130, 218),
            'spectrogram/focused-selection':   (0xFF, 0xA0, 0x00),
            'spectrogram/unfocused-selection': (0xA0, 0xA0, 0x60),
            'grid/comment':                    (239, 235, 231),
        },
    },
}

_DEFAULT_HOTKEYS = {
    'global': [
        ('Ctrl+Shift+N', 'file/new'),
        ('Ctrl+O', 'file/open'),
        ('Ctrl+S', 'file/save'),
        ('Ctrl+Shift+S', 'file/save-as'),
        ('Ctrl+Q', 'file/quit'),
        ('Ctrl+G', 'grid/jump-to-line'),
        ('Ctrl+Shift+G', 'grid/jump-to-time'),
        ('Ctrl+K', 'grid/select-prev-sub'),
        ('Ctrl+J', 'grid/select-next-sub'),
        ('Ctrl+A', 'grid/select-all'),
        ('Ctrl+Shift+A', 'grid/select-nothing'),
        ('Alt+1', 'video/play-around-sel-start', -500, 0),
        ('Alt+2', 'video/play-around-sel-start', 0, 500),
        ('Alt+3', 'video/play-around-sel-end', -500, 0),
        ('Alt+4', 'video/play-around-sel-end', 0, 500),
        ('Ctrl+R', 'video/play-around-sel', 0, 0),
        ('Ctrl+,', 'video/step-frame', -1),
        ('Ctrl+.', 'video/step-frame', 1),
        ('Ctrl+Shift+,', 'video/step-frame', -10),
        ('Ctrl+Shift+.', 'video/step-frame', 10),
        ('Ctrl+T', 'video/play-current-line'),
        ('Ctrl+P', 'video/toggle-pause'),
        ('Ctrl+Z', 'edit/undo'),
        ('Ctrl+Y', 'edit/redo'),
        ('Ctrl+F', 'edit/search'),
        ('Ctrl+H', 'edit/search-and-replace'),
        ('Alt+C', 'grid/copy-text-to-clipboard'),
        ('Ctrl+Return', 'edit/insert-below'),
        ('Ctrl+Delete', 'edit/delete'),
        ('Ctrl+Shift+1', 'audio/shift-sel-start', -250),
        ('Ctrl+Shift+2', 'audio/shift-sel-start', 250),
        ('Ctrl+Shift+3', 'audio/shift-sel-end', -250),
        ('Ctrl+Shift+4', 'audio/shift-sel-end', 250),
        ('Ctrl+1', 'audio/shift-sel-start', -25),
        ('Ctrl+2', 'audio/shift-sel-start', 25),
        ('Ctrl+3', 'audio/shift-sel-end', -25),
        ('Ctrl+4', 'audio/shift-sel-end', 25),
        ('Ctrl+B', 'audio/snap-sel-start-to-video'),
        ('Ctrl+N', 'audio/snap-sel-to-video'),
        ('Ctrl+M', 'audio/snap-sel-end-to-video'),
        ('Ctrl+[', 'video/set-playback-speed', 0.5),
        ('Ctrl+]', 'video/set-playback-speed', 1),
        ('F3', 'edit/search-repeat', 1),
        ('Shift+F3', 'edit/search-repeat', -1),
    ],

    'audio': [
        ('Shift+1', 'audio/shift-sel-start', -250),
        ('Shift+2', 'audio/shift-sel-start', 250),
        ('Shift+3', 'audio/shift-sel-end', -250),
        ('Shift+4', 'audio/shift-sel-end', 250),
        ('1', 'audio/shift-sel-start', -25),
        ('2', 'audio/shift-sel-start', 25),
        ('3', 'audio/shift-sel-end', -25),
        ('4', 'audio/shift-sel-end', 25),
        ('C', 'audio/commit-sel'),
        ('K', 'edit/insert-above'),
        ('J', 'edit/insert-below'),
        ('R', 'video/play-around-sel', 0, 0),
        ('T', 'video/play-current-line'),
        ('P', 'video/toggle-pause'),
        ('Shift+K', 'grid/select-prev-sub'),
        ('Shift+J', 'grid/select-next-sub'),
        ('A', 'audio/scroll', -1),
        ('F', 'audio/scroll', 1),
        (',', 'video/step-frame', -1),
        ('.', 'video/step-frame', 1),
        ('Shift+,', 'video/step-frame', -10),
        ('Shift+.', 'video/step-frame', 10),
        ('B', 'audio/snap-sel-start-to-video'),
        ('N', 'audio/snap-sel-to-video'),
        ('M', 'audio/snap-sel-end-to-video'),
        ('[', 'video/set-playback-speed', 0.5),
        (']', 'video/set-playback-speed', 1),
    ],
}

_DEFAULT_TOP_MENU = [
    ['&File', [
        ['file/new'],
        ['file/open'],
        ['file/save'],
        ['file/save-as'],
        None,
        ['file/load-video'],
        None,
        ['file/quit'],
    ]],

    ['&Edit', [
        ['edit/undo'],
        ['edit/redo'],
        None,
        ['grid/jump-to-line'],
        ['grid/jump-to-time'],
        ['grid/select-prev-sub'],
        ['grid/select-next-sub'],
        ['grid/select-all'],
        ['grid/select-nothing'],
        None,
        ['edit/search'],
        ['edit/search-and-replace'],
        ['edit/search-repeat', 1],
        ['edit/search-repeat', -1],
        None,
        ['edit/insert-above'],
        ['edit/insert-below'],
        ['edit/duplicate'],
        ['edit/delete'],
        None,
        ['edit/swap-text-and-notes'],
        ['edit/split-sub-at-video'],
        ['edit/karaoke-split'],
        ['edit/karaoke-join'],
        ['edit/transformation-join'],
        ['edit/join-subs/keep-first'],
        ['edit/join-subs/concatenate'],
        None,
        ['grid/copy-text-to-clipboard'],
        ['grid/copy-times-to-clipboard'],
        ['grid/paste-times-from-clipboard'],
        ['grid/copy-to-clipboard'],
        ['grid/paste-from-clipboard-above'],
        ['grid/paste-from-clipboard-below'],
        None,
        ['edit/spell-check'],
        ['edit/manage-styles'],
    ]],

    ['&View', [
        ['view/set-palette', 'light'],
        ['view/set-palette', 'dark'],
        None,
        ['grid/create-audio-sample'],
        ['video/screenshot', False],
        ['video/screenshot', True],
        None,
        ['view/focus-text-editor'],
        ['view/focus-note-editor'],
        ['view/focus-grid'],
        ['view/focus-spectrogram'],
    ]],

    ['&Playback', [
        ['Play around selection', [
            ['video/play-around-sel-start', -500, 0],
            ['video/play-around-sel-start', 0, 500],
            ['video/play-around-sel-end', -500, 0],
            ['video/play-around-sel-end', 0, 500],
        ]],
        ['video/play-around-sel', 0, 0],
        ['video/play-current-line'],
        ['video/unpause'],
        None,
        ['video/step-frame', -1],
        ['video/step-frame', 1],
        ['video/step-frame', -10],
        ['video/step-frame', 10],
        None,
        ['video/pause'],
        ['video/toggle-pause'],
        None,
        ['video/set-playback-speed', 0.5],
        ['video/set-playback-speed', 1],
    ]],

    ['&Timing', [
        ['Snap selection to subtitles', [
            ['audio/snap-sel-start-to-prev-sub'],
            ['audio/snap-sel-end-to-next-sub'],
        ]],
        ['Snap selection to video frame', [
            ['audio/snap-sel-start-to-video'],
            ['audio/snap-sel-end-to-video'],
            ['audio/snap-sel-to-video'],
        ]],
        ['Shift selection', [
            ['audio/shift-sel-start', -250],
            ['audio/shift-sel-start', 250],
            ['audio/shift-sel-end', -250],
            ['audio/shift-sel-end', 250],
            ['audio/shift-sel-start', -25],
            ['audio/shift-sel-start', 25],
            ['audio/shift-sel-end', -25],
            ['audio/shift-sel-end', 25],
        ]],
        ['audio/commit-sel'],
        None,
        ['edit/shift-subs-with-gui'],
        None,
        ['audio/scroll', -1],
        ['audio/scroll', 1],
    ]],
]

_DEFAULT_CONTEXT_MENU = [
    ['grid/create-audio-sample'],
    None,
    ['edit/insert-above'],
    ['edit/insert-below'],
    None,
    ['edit/duplicate'],
    ['edit/split-sub-at-video'],
    None,
    ['edit/join-subs/keep-first'],
    ['edit/join-subs/concatenate'],
    ['edit/karaoke-join'],
    ['edit/transformation-join'],
    None,
    ['edit/karaoke-split'],
    ['edit/snap-subs-start-to-prev-sub'],
    ['edit/snap-subs-end-to-next-sub'],
    None,
    ['edit/delete'],
]


class Serializer:
    def __init__(self, location):
        self._location = location

    @property
    def _hotkeys_path(self):
        return self._location / 'hotkey.json'

    @property
    def _menu_path(self):
        return self._location / 'menu.json'

    @property
    def _general_path(self):
        return self._location / 'general.json'

    def load(self):
        hotkeys = None
        menu = None
        general = None
        if self._hotkeys_path.exists():
            hotkeys = json.loads(self._hotkeys_path.read_text())
        if self._menu_path.exists():
            menu = json.loads(self._menu_path.read_text())
        if self._general_path.exists():
            general = json.loads(self._general_path.read_text())
        return hotkeys, menu, general

    def write(self, hotkeys, menu, general):
        self._location.mkdir(parents=True, exist_ok=True)
        self._hotkeys_path.write_text(json.dumps(hotkeys, indent=4))
        self._menu_path.write_text(json.dumps(menu, indent=4))
        self._general_path.write_text(json.dumps(general, indent=4))


class Options:
    DEFAULT_PATH = Path(xdg.XDG_CONFIG_HOME) / 'bubblesub'

    def __init__(self):
        self.general = _DEFAULT_GENERAL
        self.hotkeys = _DEFAULT_HOTKEYS
        self.main_menu = _DEFAULT_TOP_MENU
        self.context_menu = _DEFAULT_CONTEXT_MENU
        self.location = None

    def load(self, location):
        self.location = location
        serializer = Serializer(location)
        hotkeys, menu, general = serializer.load()
        if hotkeys:
            self.hotkeys = hotkeys
        if menu:
            self.main_menu = menu['main']
            self.context_menu = menu['context']
        if general:
            self.general = general
        self._ensure_defaults(self.general, _DEFAULT_GENERAL)

    def save(self, location):
        serializer = Serializer(location)
        serializer.write(
            self.hotkeys,
            {'main': self.main_menu, 'context': self.context_menu},
            self.general)

    def _ensure_defaults(self, target, source):
        if isinstance(source, list) or isinstance(source, tuple):
            if not isinstance(target, list):
                raise RuntimeError('Expected list')
        elif isinstance(source, dict):
            if not isinstance(target, dict):
                raise RuntimeError('Expected dictionary')
            for key, value in source.items():
                if key not in target:
                    target[key] = value
                else:
                    self._ensure_defaults(target[key], value)
        elif type(target) != type(source):
            raise RuntimeError(f'Expected {type(source)}')
