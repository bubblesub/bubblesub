"""Base config."""
import abc
from pathlib import Path


class BaseConfig(abc.ABC):
    """Base config."""

    @property
    @abc.abstractmethod
    def file_name(self) -> str:
        """Config file name."""
        raise NotImplementedError('Not implemented')

    @abc.abstractmethod
    def loads(self, text: str) -> None:
        """
        Load internals from a human readable representation.

        :param text: INI, JSON, etc.
        """
        raise NotImplementedError('Not implemented')

    @abc.abstractmethod
    def dumps(self) -> str:
        """
        Serialize internals to a human readable representation.

        :return: INI, JSON etc.
        """
        raise NotImplementedError('Not implemented')

    def load(self, root_dir: Path) -> None:
        """
        Load internals of this config from the specified directory.

        :param root_dir: directory where to look for the matching config file
        """
        full_path = root_dir / self.file_name
        if full_path.exists():
            self.loads(full_path.read_text())

    def save(self, root_dir: Path) -> None:
        """
        Save internals of this config to a specified directory.

        :param root_dir: directory where to look for the matching config file
        """
        full_path = root_dir / self.file_name
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(self.dumps())
