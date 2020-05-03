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

"""Program configuration."""

from pathlib import Path

from bubblesub.cfg.hotkeys import HotkeysConfig
from bubblesub.cfg.menu import MenuConfig
from bubblesub.cfg.options import OptionsConfig
from bubblesub.data import USER_CONFIG_DIR


class Config:
    """Umbrella class containing all the configuration."""

    DEFAULT_PATH = USER_CONFIG_DIR / "bubblesub"

    def __init__(self) -> None:
        """Initialize self."""
        self.opt = OptionsConfig()
        self.hotkeys = HotkeysConfig()
        self.menu = MenuConfig()
        self.root_dir = Path()

    def load(self, root_dir: Path) -> None:
        """Load configuration from the specified path.

        :param root_dir: root directory to load the configuration from
        """
        self.root_dir = root_dir
        self.opt.load(root_dir)
        self.hotkeys.load(root_dir)
        self.menu.load(root_dir)

    def save(self, root_dir: Path) -> None:
        """Save configuration to the specified path.

        :param root_dir: root directory to save the configuration to
        """
        self.opt.save(root_dir)
        self.hotkeys.create_example_file(root_dir)
        self.menu.create_example_file(root_dir)
