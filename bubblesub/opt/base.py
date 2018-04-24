import abc
from pathlib import Path


class BaseConfig(abc.ABC):
    @property
    @abc.abstractmethod
    def file_name(self) -> str:
        raise NotImplementedError('Not implemented')

    @abc.abstractmethod
    def loads(self, text: str) -> None:
        raise NotImplementedError('Not implemented')

    @abc.abstractmethod
    def dumps(self) -> str:
        raise NotImplementedError('Not implemented')

    def load(self, root_dir: Path) -> None:
        full_path = root_dir / self.file_name
        if full_path.exists():
            self.loads(full_path.read_text())

    def save(self, root_dir: Path) -> None:
        full_path = root_dir / self.file_name
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(self.dumps())
