"""Program options."""
import typing as T
from pathlib import Path

import xdg

from bubblesub.opt.general import GeneralConfig
from bubblesub.opt.hotkeys import HotkeysConfig
from bubblesub.opt.menu import MenuConfig


class Options:
    """Umbrella class containing all the configuration."""

    DEFAULT_PATH = Path(xdg.XDG_CONFIG_HOME) / 'bubblesub'

    def __init__(self) -> None:
        """Initialize self."""
        self.general = GeneralConfig()
        self.hotkeys = HotkeysConfig()
        self.menu = MenuConfig()
        self.root_dir: T.Optional[Path] = None

    @property
    def _hotkeys_path(self) -> Path:
        return self.root_dir / 'hotkey.json'

    @property
    def _menu_path(self) -> Path:
        return self.root_dir / 'menu.json'

    @property
    def _general_path(self) -> Path:
        return self.root_dir / 'general.ini'

    def load(self, root_dir: Path) -> None:
        """
        Load configuration from the specified path.

        :param root_dir: root directory to load the configuration from
        """
        self.root_dir = root_dir
        self.general.load(root_dir)
        self.hotkeys.load(root_dir)
        self.menu.load(root_dir)

    def save(self, root_dir: Path) -> None:
        """
        Save configuration to the specified path.

        :param root_dir: root directory to save the configuration to
        """
        self.general.save(root_dir)
        self.hotkeys.save(root_dir)
        self.menu.save(root_dir)
