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
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Optional

from PyQt5 import QtCore

from bubblesub.cfg.base import ConfigError, SubConfig
from bubblesub.data import DATA_DIR


def _get_user_path(root_dir: Path) -> Path:
    return root_dir / "hotkeys.conf"


class HotkeyContext(enum.Enum):
    """Which GUI widget the hotkey works in."""

    GLOBAL = "global"
    SPECTROGRAM = "spectrogram"
    SUBTITLES_GRID = "subtitles_grid"


class Hotkey:
    """Hotkey definition."""

    def __init__(
        self, context: HotkeyContext, shortcut: str, cmdline: str
    ) -> None:
        """Initialize self.

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

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__()
        self._hotkeys: list[Hotkey] = []
        self._signals = _HotkeysConfigSignals()
        self.load(None)

    def create_example_file(self, root_dir: Path) -> None:
        """Create an example file for the user to get to know the config
        syntax.

        :param root_dir: directory where to put the config file
        """
        user_path = _get_user_path(root_dir)
        if not user_path.exists():
            user_path.write_text((DATA_DIR / "hotkeys.example").read_text())

    def load(self, root_dir: Optional[Path]) -> None:
        """Load internals of this config from the specified directory.

        :param root_dir: directory where to look for the matching config file
        """
        self._hotkeys.clear()
        self._loads((DATA_DIR / "hotkeys.conf").read_text())
        if root_dir:
            user_path = _get_user_path(root_dir)
            if user_path.exists():
                try:
                    self._loads(user_path.read_text())
                except ConfigError as ex:
                    raise ConfigError(f"error loading {user_path}: {ex}")

    def _loads(self, text: str) -> None:
        cur_context = HotkeyContext.GLOBAL
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

    def __iter__(self) -> Iterator[Hotkey]:
        """Let users iterate directly over this config.

        :return: iterator
        """
        return iter(self._hotkeys)

    def __getitem__(self, key: Any) -> Optional[str]:
        """Retrieve hotkey cmdline by shortcut.

        :param key: shortcut
        :return: hotkey cmdline if found, None otherwise
        """
        context, shortcut = key
        for hotkey in self._hotkeys:
            if hotkey.context == context and hotkey.shortcut == shortcut:
                return hotkey.cmdline
        return None

    def __setitem__(self, key: Any, cmdline: Optional[str]) -> None:
        """Update hotkey cmdline by shortcut.
        If cmdline is None, remove the hotkey.

        :param key: shortcut to update
        :param cmdline: cmdline to set
        """
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

        if cmdline is None:
            return

        hotkey = Hotkey(context=context, shortcut=shortcut, cmdline=cmdline)
        self._hotkeys.append(hotkey)
        self.added.emit(hotkey)

    def _parse_key(self, key: Any) -> tuple[HotkeyContext, str]:
        msg = "key must be a context-shortcut tuple"
        assert isinstance(key, tuple), msg
        assert len(key) == 2, msg
        assert isinstance(key[0], HotkeyContext), msg
        assert isinstance(key[1], str), msg
        return (key[0], key[1])
