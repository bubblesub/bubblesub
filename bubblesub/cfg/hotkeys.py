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
import re
import typing as T
from pathlib import Path

from PyQt5 import QtCore

from bubblesub.cfg.base import ConfigError, SubConfig
from bubblesub.data import ROOT_DIR


class HotkeyContext(enum.Enum):
    """Which GUI widget the hotkey works in."""

    Global = "global"
    Spectrogram = "spectrogram"
    SubtitlesGrid = "subtitles_grid"


class Hotkey:
    """Hotkey definition."""

    def __init__(
        self, context: HotkeyContext, shortcut: str, cmdline: str
    ) -> None:
        """
        Initialize self.

        :param context: context in the gui the hotkey works for
        :param shortcut: key combination that activates the hotkey
        :param cmdline: command line to execute
        """
        self.context = context
        self.shortcut = shortcut
        self.cmdline = cmdline


class _HotkeysConfigSignals(QtCore.QObject):
    # QObject doesn't play nice with multiple inheritance, hence composition
    changed = QtCore.pyqtSignal([Hotkey])
    added = QtCore.pyqtSignal([Hotkey])
    deleted = QtCore.pyqtSignal([Hotkey])


class HotkeysConfig(SubConfig):
    """Configuration for global and widget-centric GUI hotkeys."""

    changed = property(lambda self: self._signals.changed)
    added = property(lambda self: self._signals.added)
    deleted = property(lambda self: self._signals.deleted)
    file_name = "hotkeys.conf"

    def __init__(self) -> None:
        """Initialize self."""
        self._hotkeys: T.List[Hotkey] = []
        self._signals = _HotkeysConfigSignals()
        super().__init__()

    def _clear(self) -> None:
        self._hotkeys.clear()

    def _loads(self, text: str) -> None:
        cur_context = HotkeyContext.Global
        for i, line in enumerate(text.split("\n"), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            match = re.match(r"^\[(.*)\]$", line)
            if match:
                try:
                    cur_context = HotkeyContext(match.group(1))
                except ValueError:
                    raise ConfigError(
                        f'"{match.group(1)}" is not a valid hotkey context'
                    )
                continue

            try:
                shortcut, cmdline = re.split(r"\s+", line, maxsplit=1)
            except ValueError:
                raise ConfigError(f"syntax error near line #{i} ({line})")
            self._hotkeys.append(
                Hotkey(context=cur_context, shortcut=shortcut, cmdline=cmdline)
            )

    def create_example_file(self, root_dir: Path) -> None:
        """
        Create an example file for the user to get to know the config syntax.

        :param root_dir: directory where to put the config file
        """
        full_path = root_dir / self.file_name
        if not full_path.exists():
            full_path.write_text(
                (ROOT_DIR / self.file_name).with_suffix(".example").read_text()
            )

    def __iter__(self) -> T.Iterator[Hotkey]:
        """
        Let users iterate directly over this config.

        :return: iterator
        """
        return iter(self._hotkeys)

    def __getitem__(self, key: T.Any) -> T.Optional[str]:
        context, shortcut = key
        for hotkey in self._hotkeys:
            if hotkey.context == context and hotkey.shortcut == shortcut:
                return hotkey.cmdline
        return None

    def __setitem__(self, key: T.Any, cmdline: T.Optional[str]) -> None:
        context, shortcut = self._parse_key(key)

        for i, hotkey in enumerate(self._hotkeys):
            if (
                hotkey.context == context
                and hotkey.shortcut.lower() == shortcut.lower()
            ):
                if cmdline is None:
                    self.deleted.emit(self._hotkeys[i])
                    del self._hotkeys[i]
                elif cmdline != hotkey.cmdline:
                    hotkey.cmdline = cmdline
                    self.changed.emit(hotkey)
                return

        hotkey = Hotkey(context=context, shortcut=shortcut, cmdline=cmdline)
        self._hotkeys.append(hotkey)
        self.added.emit(hotkey)

    def _parse_key(self, key: T.Any) -> T.Tuple[HotkeyContext, str]:
        msg = "key must be a context-shortcut tuple"
        assert isinstance(key, tuple), msg
        assert len(key) == 2, msg
        assert isinstance(key[0], HotkeyContext), msg
        assert isinstance(key[1], str), msg
        return (key[0], key[1])
