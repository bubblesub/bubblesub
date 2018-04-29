"""General config."""

import configparser
import enum
import io
import json
import re
import typing as T

from bubblesub.opt.base import BaseConfig


class SubsModelColumn(enum.IntEnum):
    """Column indices in subtitles grid."""

    Start = 0
    End = 1
    Style = 2
    Actor = 3
    Text = 4
    Note = 5
    Duration = 6
    CharsPerSec = 7


class SearchMode(enum.IntEnum):
    """Search mode in subtitles grid."""

    Text = 1
    Note = 2
    Actor = 3
    Style = 4


PALETTE_DARK: T.Dict[str, T.Tuple[int, ...]] = {
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
    'spectrogram/keyframe':            (200, 100, 0),
    'spectrogram/selected-sub-text':   (255, 255, 255),
    'spectrogram/selected-sub-line':   (42, 130, 218, 220),
    'spectrogram/selected-sub-fill':   (42, 130, 218, 50),
    'spectrogram/unselected-sub-text': (100, 100, 100),
    'spectrogram/unselected-sub-line': (42, 130, 218, 120),
    'spectrogram/unselected-sub-fill': (42, 130, 218, 30),
    'spectrogram/focused-sel-line':    (144, 160, 0, 220),
    'spectrogram/focused-sel-fill':    (160, 255, 0, 60),
    'spectrogram/unfocused-sel-line':  (144, 160, 0, 110),
    'spectrogram/unfocused-sel-fill':  (160, 255, 0, 30),
    'grid/ass-mark':                   (255, 100, 100),
    'grid/non-printing-mark':          (100, 70, 40),
    'grid/comment':                    (53, 53, 53),
    'console/error':                   (255, 0, 0),
    'console/warning':                 (200, 100, 0),
    'console/info':                    (255, 255, 255),
    'console/debug':                   (0, 100, 200),
}

PALETTE_LIGHT: T.Dict[str, T.Tuple[int, ...]] = {
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
    'spectrogram/keyframe':            (255, 128, 0),
    'spectrogram/selected-sub-text':   (255, 255, 255),
    'spectrogram/selected-sub-line':   (42, 130, 218, 220),
    'spectrogram/selected-sub-fill':   (42, 130, 218, 50),
    'spectrogram/unselected-sub-text': (0, 0, 0),
    'spectrogram/unselected-sub-line': (42, 130, 218, 120),
    'spectrogram/unselected-sub-fill': (42, 130, 218, 30),
    'spectrogram/focused-sel-line':    (144, 160, 0, 220),
    'spectrogram/focused-sel-fill':    (160, 255, 0, 60),
    'spectrogram/unfocused-sel-line':  (144, 160, 0, 110),
    'spectrogram/unfocused-sel-fill':  (160, 255, 0, 30),
    'grid/ass-mark':                   (230, 0, 0),
    'grid/non-printing-mark':          (230, 200, 170),
    'grid/comment':                    (239, 235, 231),

    'console/error':                   (255, 0, 0),
    'console/warning':                 (200, 100, 0),
    'console/info':                    (0, 0, 0),
    'console/debug':                   (0, 100, 200),
}


def _serialize_color(color: T.Tuple[int, ...]) -> str:
    """
    Convert internal color representation to a human readable form.

    :param color: tuple with color components
    :return: text in form of `#FFFFFF`
    """
    return '#' + ''.join(f'{component:02X}' for component in color)


def _deserialize_color(color: str) -> T.Tuple[int, ...]:
    """
    Convert a human readable color to internal representation.

    :param color: text in form of `#FFFFFF`
    :return: tuple with color components
    """
    return tuple(
        int(match.group(1), 16)
        for match in re.finditer('([0-9a-fA-F]{2})', color.lstrip('#'))
    )


class SubtitlesConfig:
    """Config related to subtitles."""

    def __init__(self) -> None:
        """Initialize self."""
        self.max_characters_per_second = 15
        self.default_duration = 2000


class VideoConfig:
    """Config related to video and playback."""

    def __init__(self) -> None:
        """Initialize self."""
        self.subs_sync_interval = 65


class AudioConfig:
    """Config related to audio and spectrogram."""

    def __init__(self) -> None:
        """Initialize self."""
        self.spectrogram_resolution = 10
        self.spectrogram_sync_interval = 65


class SearchConfig:
    """Config related to search in subtitle grid."""

    def __init__(self) -> None:
        """Initialize self."""
        self.history: T.List[str] = []
        self.case_sensitive = False
        self.use_regexes = False
        self.mode = SearchMode.Text


class GeneralConfig(BaseConfig):
    """General config."""

    file_name = 'general.ini'

    def __init__(self) -> None:
        """Initialize self."""
        self.spell_check = 'en_US'
        self.convert_newlines = True
        self.grid_columns = [col.name for col in SubsModelColumn]
        self.splitters: T.Dict[str, str] = {}

        self.current_palette = 'light'
        self.palettes: T.Dict[str, T.Dict[str, T.Tuple[int, ...]]] = {
            'dark': PALETTE_DARK,
            'light': PALETTE_LIGHT,
        }

        self.fonts = {
            'editor': '',
            'notes': '',
        }

        self.subs = SubtitlesConfig()
        self.audio = AudioConfig()
        self.video = VideoConfig()
        self.search = SearchConfig()

    def loads(self, text: str) -> None:
        """
        Load internals from a human readable representation.

        :param text: INI
        """
        cfg = configparser.RawConfigParser()
        cfg.optionxform = lambda option: option
        cfg.read_string(text)

        self.spell_check = cfg.get(
            'basic', 'spell_check', fallback=self.spell_check
        )
        self.convert_newlines = cfg.getboolean(
            'basic', 'convert_newlines', fallback=self.convert_newlines
        )
        if cfg.get('basic', 'grid_columns', fallback=None):
            self.grid_columns = cfg.get('basic', 'grid_columns').split(',')
        else:
            self.grid_columns = [col.name for col in SubsModelColumn]
        self.current_palette = (
            cfg.get('basic', 'current_palette', fallback=self.current_palette)
        )
        for key, value in cfg.items('splitters'):
            self.splitters[key] = value
        for key, value in self.fonts.items():
            self.fonts[key] = cfg.get('fonts', key, fallback=value)

        self.audio.spectrogram_resolution = cfg.getint(
            'audio',
            'spectrogram_resolution',
            fallback=self.audio.spectrogram_resolution
        )
        self.audio.spectrogram_sync_interval = cfg.getint(
            'audio',
            'spectrogram_sync_interval',
            fallback=self.audio.spectrogram_sync_interval
        )

        self.video.subs_sync_interval = cfg.getint(
            'video',
            'subs_sync_interval',
            fallback=self.video.subs_sync_interval
        )

        self.subs.max_characters_per_second = cfg.getint(
            'subs',
            'max_characters_per_second',
            fallback=self.subs.max_characters_per_second
        )
        self.subs.default_duration = cfg.getint(
            'subs',
            'default_duration',
            fallback=self.subs.default_duration
        )

        self.search.case_sensitive = cfg.getboolean(
            'search', 'case_sensitive', fallback=self.search.case_sensitive
        )
        self.search.use_regexes = cfg.getboolean(
            'search', 'use_regexes', fallback=self.search.use_regexes
        )
        self.search.mode = SearchMode(
            cfg.getint('search', 'mode', fallback=self.search.mode)
        )
        self.search.history = json.loads(
            cfg.get('search', 'history', fallback='[]')
        )

        self.palettes.clear()
        if any(section.startswith('palette.') for section in cfg.sections()):
            for section_name, section in cfg.items():
                match = re.match(r'^palette\.(\w+)$', section_name)
                if match:
                    palette_name = match.group(1)
                    self.palettes[palette_name] = {
                        key: _deserialize_color(value)
                        for key, value in section.items()
                    }

    def dumps(self) -> str:
        """
        Save internals from a human readable representation.

        :return: INI
        """
        cfg = configparser.RawConfigParser()
        cfg.optionxform = lambda option: option
        cfg.read_dict(
            {
                'basic':
                {
                    'spell_check': self.spell_check,
                    'convert_newlines': self.convert_newlines,
                    'grid_columns': ','.join(self.grid_columns),
                    'current_palette': self.current_palette,
                },

                'splitters': self.splitters,

                'fonts': self.fonts,

                'audio':
                {
                    'spectrogram_resolution':
                        self.audio.spectrogram_resolution,
                    'spectrogram_sync_interval':
                        self.audio.spectrogram_sync_interval,
                },

                'video':
                {
                    'subs_sync_interval': self.video.subs_sync_interval
                },

                'subs':
                {
                    'max_characters_per_second':
                        self.subs.max_characters_per_second,
                    'default_duration': self.subs.default_duration
                },

                'search':
                {
                    'history': json.dumps(self.search.history),
                    'case_sensitive': self.search.case_sensitive,
                    'use_regexes': self.search.use_regexes,
                    'mode': int(self.search.mode),
                }
            }
        )

        cfg.read_dict(
            {
                f'palette.{palette_name}':
                {
                    key: _serialize_color(color)
                    for key, color in palette.items()
                }
                for palette_name, palette in self.palettes.items()
            }
        )

        with io.StringIO() as handle:
            cfg.write(handle)
            handle.seek(0)
            return handle.read()
