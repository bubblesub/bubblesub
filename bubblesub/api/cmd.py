import abc
import asyncio
import importlib.util
import inspect
import sys
import time
import traceback
import typing as T
from pathlib import Path

from PyQt5 import QtCore

import bubblesub.api.api
import bubblesub.model


class BaseCommand(abc.ABC):
    def __init__(self, api: 'bubblesub.api.api.Api', *_args: T.Any) -> None:
        self.api = api

    @bubblesub.model.classproperty
    @abc.abstractproperty
    def name(cls) -> str:
        raise NotImplementedError('Command has no name')

    @property
    @abc.abstractproperty
    def menu_name(self) -> str:
        raise NotImplementedError('Command has no menu name')

    @property
    def is_enabled(self) -> bool:
        return True

    @abc.abstractmethod
    async def run(self) -> None:
        raise NotImplementedError('Command has no implementation')

    def debug(self, text: str) -> None:
        self.api.log.debug(f'cmd/{self.name}: {text}')

    def info(self, text: str) -> None:
        self.api.log.info(f'cmd/{self.name}: {text}')

    def warn(self, text: str) -> None:
        self.api.log.warn(f'cmd/{self.name}: {text}')

    def error(self, text: str) -> None:
        self.api.log.error(f'cmd/{self.name}: {text}')


class CommandApi(QtCore.QObject):
    core_registry: T.Dict[str, T.Type] = {}
    plugin_registry: T.Dict[str, T.Type] = {}
    plugins_loaded = QtCore.pyqtSignal()

    def __init__(self, api: 'bubblesub.api.Api') -> None:
        super().__init__()
        self._api = api
        self._thread = None

    def run(self, cmd: BaseCommand) -> None:
        if not cmd.is_enabled:
            self._api.log.info(f'cmd/{cmd.name}: not available right now')
            return

        async def run() -> None:
            self._api.log.info('cmd/{}: running...'.format(cmd.name))
            start_time = time.time()
            try:
                await cmd.run()
            except Exception as ex:
                self._api.log.error('cmd/{}: {}'.format(cmd.name, ex))
                traceback.print_exc()
            end_time = time.time()
            took = end_time - start_time
            self._api.log.info(f'cmd/{cmd.name}: ran in {took:.02f} s')

        asyncio.ensure_future(run())

    def get(self, name: str, args: T.Any) -> BaseCommand:
        ret = self.plugin_registry.get(name)
        if not ret:
            ret = self.core_registry.get(name)
        if not ret:
            raise KeyError('No command named {}'.format(name))
        try:
            return T.cast(BaseCommand, ret(self._api, *args))
        except Exception:
            print('Error creating command {}'.format(name), file=sys.stderr)
            raise

    def load_plugins(self, path: Path) -> None:
        self.plugin_registry.clear()
        specs = []
        if path.exists():
            for subpath in path.glob('*.py'):
                spec = importlib.util.spec_from_file_location(
                    'bubblesub.plugin', str(subpath)
                )
                if spec is not None:
                    specs.append(spec)
        try:
            for spec in specs:
                spec.loader.exec_module(importlib.util.module_from_spec(spec))
        finally:
            self.plugins_loaded.emit()


class CoreCommand(BaseCommand):
    def __init_subclass__(cls) -> None:
        if not inspect.isabstract(cls):
            print('registering', cls, 'as', cls.name)
            CommandApi.core_registry[cls.name] = cls


class PluginCommand(BaseCommand):
    def __init_subclass__(cls) -> None:
        if not inspect.isabstract(cls):
            print('registering', cls, 'as', cls.name)
            CommandApi.plugin_registry[cls.name] = cls
