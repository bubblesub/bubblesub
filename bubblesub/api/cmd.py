import abc
import asyncio
import inspect
import time
import sys
import traceback
import importlib.util

from PyQt5 import QtCore

import bubblesub.model


class BaseCommand(abc.ABC):
    def __init__(self, api, *_args):
        self.api = api

    @bubblesub.model.classproperty
    @abc.abstractproperty
    def name(cls):
        raise NotImplementedError('Command has no name')

    @property
    @abc.abstractproperty
    def menu_name(self):
        raise NotImplementedError('Command has no menu name')

    @property
    def is_enabled(self):
        return True

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError('Command has no implementation')

    def debug(self, text):
        self.api.log.debug('cmd/{}: {}'.format(self.name, text))

    def info(self, text):
        self.api.log.info('cmd/{}: {}'.format(self.name, text))

    def warn(self, text):
        self.api.log.warn('cmd/{}: {}'.format(self.name, text))

    def error(self, text):
        self.api.log.error('cmd/{}: {}'.format(self.name, text))


class CommandApi(QtCore.QObject):
    core_registry = {}
    plugin_registry = {}
    plugins_loaded = QtCore.pyqtSignal()

    def __init__(self, api):
        super().__init__()
        self._api = api
        self._thread = None

    def run(self, cmd):
        if not cmd.is_enabled:
            self._api.log.info(
                'cmd/{}: not available right now'.format(cmd.name))
            return

        async def run():
            self._api.log.info('cmd/{}: running...'.format(cmd.name))
            start_time = time.time()
            try:
                await cmd.run()
            except Exception as ex:
                self._api.log.error('cmd/{}: {}'.format(cmd.name, ex))
                traceback.print_exc()
            end_time = time.time()
            self._api.log.info('cmd/{}: ran in {:.02f} s'.format(
                cmd.name, end_time - start_time))

        asyncio.ensure_future(run())

    def get(self, name, args):
        ret = self.plugin_registry.get(name)
        if not ret:
            ret = self.core_registry.get(name)
        if not ret:
            raise KeyError('No command named {}'.format(name))
        try:
            return ret(self._api, *args)
        except Exception:
            print('Error creating command {}'.format(name), file=sys.stderr)
            raise

    def load_plugins(self, path):
        self.plugin_registry.clear()
        specs = []
        if path.exists():
            for subpath in path.glob('*.py'):
                spec = importlib.util.spec_from_file_location(
                    'bubblesub.plugin', subpath)
                if spec is not None:
                    specs.append(spec)
        try:
            for spec in specs:
                spec.loader.exec_module(importlib.util.module_from_spec(spec))
        finally:
            self.plugins_loaded.emit()


class CoreCommand(BaseCommand):
    def __init_subclass__(cls):
        if not inspect.isabstract(cls):
            print('registering', cls, 'as', cls.name)
            CommandApi.core_registry[cls.name] = cls


class PluginCommand(BaseCommand):
    def __init_subclass__(cls):
        if not inspect.isabstract(cls):
            print('registering', cls, 'as', cls.name)
            CommandApi.plugin_registry[cls.name] = cls
