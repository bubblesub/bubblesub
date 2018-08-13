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

"""General config."""

import base64
import configparser
import enum
import io
import json
import re
import typing as T
import zlib

from bubblesub.opt.base import BaseConfig


def _decompress(data: T.Optional[str]) -> T.Optional[bytes]:
    if data is None:
        return None
    return zlib.decompress(base64.b64decode(data))


def _compress(data: T.Optional[bytes]) -> T.Optional[str]:
    if data is None:
        return None
    return base64.b64encode(zlib.compress(data)).decode('ascii')


class SubtitlesModelColumn(enum.IntEnum):
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
    'grid/comment':                    (53, 53, 53),
    'console/error':                   (255, 0, 0),
    'console/warning':                 (200, 100, 0),
    'console/info':                    (255, 255, 255),
    'console/debug':                   (0, 100, 200),
    'console/timestamp':               (130, 130, 130),
    'console/command':                 (100, 200, 100),
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
    'grid/comment':                    (239, 235, 231),

    'console/error':                   (255, 0, 0),
    'console/warning':                 (200, 100, 0),
    'console/info':                    (0, 0, 0),
    'console/debug':                   (0, 100, 200),
    'console/timestamp':               (120, 120, 120),
    'console/command':                 (0, 128, 0),
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

    def loads(self, cfg: configparser.RawConfigParser) -> None:
        """
        Load internals from the specified config parser.

        :param cfg: config parser
        """
        self.max_characters_per_second = cfg.getint(
            'subs',
            'max_characters_per_second',
            fallback=self.max_characters_per_second
        )
        self.default_duration = cfg.getint(
            'subs',
            'default_duration',
            fallback=self.default_duration
        )

    def dumps(self) -> T.Any:
        """
        Dump internals.

        :return: config parser-compatible structure
        """
        return {
            'subs':
            {
                'max_characters_per_second': self.max_characters_per_second,
                'default_duration': self.default_duration
            }
        }


class StylesConfig:
    """Config related to subtitle styles."""

    def __init__(self) -> None:
        """Initialize self."""
        self.preview_test_text = 'Test テスト\n0123456789'
        self.preview_background = 'transparency-grid.png'

    def loads(self, cfg: configparser.RawConfigParser) -> None:
        """
        Load internals from the specified config parser.

        :param cfg: config parser
        """
        self.preview_test_text = cfg.get(
            'styles',
            'preview_test_text',
            fallback=self.preview_test_text
        )
        self.preview_background = cfg.get(
            'styles',
            'preview_background',
            fallback=self.preview_background
        )

    def dumps(self) -> T.Any:
        """
        Dump internals.

        :return: config parser-compatible structure
        """
        return {
            'styles':
            {
                'preview_test_text': self.preview_test_text,
                'preview_background': self.preview_background
            }
        }


class VideoConfig:
    """Config related to video and playback."""

    def __init__(self) -> None:
        """Initialize self."""
        self.subs_sync_interval = 65

    def loads(self, cfg: configparser.RawConfigParser) -> None:
        """
        Load internals from the specified config parser.

        :param cfg: config parser
        """
        self.subs_sync_interval = cfg.getint(
            'video',
            'subs_sync_interval',
            fallback=self.subs_sync_interval
        )

    def dumps(self) -> T.Any:
        """
        Dump internals.

        :return: config parser-compatible structure
        """
        return {
            'video':
            {
                'subs_sync_interval': self.subs_sync_interval
            }
        }


class AudioConfig:
    """Config related to audio and spectrogram."""

    def __init__(self) -> None:
        """Initialize self."""
        self.spectrogram_resolution = 10
        self.spectrogram_sync_interval = 65

    def loads(self, cfg: configparser.RawConfigParser) -> None:
        """
        Load internals from the specified config parser.

        :param cfg: config parser
        """
        self.spectrogram_resolution = cfg.getint(
            'audio',
            'spectrogram_resolution',
            fallback=self.spectrogram_resolution
        )
        self.spectrogram_sync_interval = cfg.getint(
            'audio',
            'spectrogram_sync_interval',
            fallback=self.spectrogram_sync_interval
        )

    def dumps(self) -> T.Any:
        """
        Dump internals.

        :return: config parser-compatible structure
        """
        return {
            'audio':
            {
                'spectrogram_resolution': self.spectrogram_resolution,
                'spectrogram_sync_interval': self.spectrogram_sync_interval
            }
        }


class SearchConfig:
    """Config related to search in subtitle grid."""

    def __init__(self) -> None:
        """Initialize self."""
        self.history: T.List[str] = []
        self.case_sensitive = False
        self.use_regexes = False
        self.mode = SearchMode.Text

    def loads(self, cfg: configparser.RawConfigParser) -> None:
        """
        Load internals from the specified config parser.

        :param cfg: config parser
        """
        self.case_sensitive = cfg.getboolean(
            'search', 'case_sensitive', fallback=self.case_sensitive
        )
        self.use_regexes = cfg.getboolean(
            'search', 'use_regexes', fallback=self.use_regexes
        )
        self.mode = SearchMode(
            cfg.getint('search', 'mode', fallback=self.mode)
        )
        self.history = json.loads(
            cfg.get('search', 'history', fallback='[]')
        )

    def dumps(self) -> T.Any:
        """
        Dump internals.

        :return: config parser-compatible structure
        """
        return {
            'search':
            {
                'history': json.dumps(self.history),
                'case_sensitive': self.case_sensitive,
                'use_regexes': self.use_regexes,
                'mode': int(self.mode)
            }
        }


class GuiConfig:
    """Config related to GUI."""

    def __init__(self) -> None:
        """Initialize self."""
        self.current_palette = 'light'
        self.splitters: T.Dict[str, bytes] = {}
        self.grid_columns: T.Optional[bytes] = None
        self.fonts = {
            'editor': '',
            'notes': '',
            'console': ''
        }
        self.palettes: T.Dict[str, T.Dict[str, T.Tuple[int, ...]]] = {
            'dark': PALETTE_DARK,
            'light': PALETTE_LIGHT,
        }

    def loads(self, cfg: configparser.RawConfigParser) -> None:
        """
        Load internals from the specified config parser.

        :param cfg: config parser
        """
        self.current_palette = (
            cfg.get('gui', 'current_palette', fallback=self.current_palette)
        )
        if cfg.get('gui', 'grid_columns', fallback=''):
            self.grid_columns = _decompress(cfg.get('gui', 'grid_columns'))
        else:
            self.grid_columns = None

        self._load_fonts(cfg)
        self._load_splitters(cfg)
        self._load_palettes(cfg)

    def _load_fonts(self, cfg: configparser.RawConfigParser) -> None:
        for key, value in self.fonts.items():
            self.fonts[key] = cfg.get('gui.fonts', key, fallback=value)

    def _load_splitters(self, cfg: configparser.RawConfigParser) -> None:
        if cfg.has_section('gui.splitters'):
            for key, raw_value in cfg.items('gui.splitters'):
                value = _decompress(raw_value)
                if value is not None:
                    self.splitters[key] = value

    def _load_palettes(self, cfg: configparser.RawConfigParser) -> None:
        new_palettes = {}
        for section_name, section in cfg.items():
            match = re.match(r'^gui.palette\.(\w+)$', section_name)
            if match:
                palette_name = match.group(1)
                new_palettes[palette_name] = {
                    key: _deserialize_color(value)
                    for key, value in section.items()
                }
        if new_palettes:
            self.palettes.clear()
            self.palettes.update(new_palettes)
        if self.current_palette not in self.palettes:
            self.current_palette = list(self.palettes.keys())[0]

    def dumps(self) -> T.Any:
        """
        Dump internals.

        :return: config parser-compatible structure
        """
        ret = {
            'gui': {
                'current_palette': self.current_palette,
                'grid_columns': _compress(self.grid_columns)
            },
            'gui.splitters': {
                key: _compress(value)
                for key, value in self.splitters.items()
            },
            'gui.fonts': self.fonts
        }

        for palette_name, palette in self.palettes.items():
            ret[f'gui.palette.{palette_name}'] = {
                key: _serialize_color(color)
                for key, color in palette.items()
            }

        return ret


class GeneralConfig(BaseConfig):
    """General config."""

    file_name = 'general.ini'

    def __init__(self) -> None:
        """Initialize self."""
        self.spell_check = 'en_US'
        self.convert_newlines = True
        self.gui = GuiConfig()

        self.subs = SubtitlesConfig()
        self.styles = StylesConfig()
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

        self.gui.loads(cfg)
        self.audio.loads(cfg)
        self.video.loads(cfg)
        self.subs.loads(cfg)
        self.styles.loads(cfg)
        self.search.loads(cfg)

    def dumps(self) -> str:
        """
        Save internals from a human readable representation.

        :return: INI
        """
        cfg = configparser.RawConfigParser()
        cfg.optionxform = lambda option: option

        cfg.read_dict({
            'basic':
            {
                'spell_check': self.spell_check,
                'convert_newlines': self.convert_newlines,
            },
        })

        cfg.read_dict(self.gui.dumps())
        cfg.read_dict(self.audio.dumps())
        cfg.read_dict(self.video.dumps())
        cfg.read_dict(self.subs.dumps())
        cfg.read_dict(self.styles.dumps())
        cfg.read_dict(self.search.dumps())

        with io.StringIO() as handle:
            cfg.write(handle)
            handle.seek(0)
            return handle.read()
