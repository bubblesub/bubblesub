import asyncio
import time
import sys
import importlib.util
import bubblesub.util


class BaseCommand:
    def __init__(self, api, *_args):
        self.api = api

    @bubblesub.util.classproperty
    def name(cls):
        raise NotImplementedError('Command has no name')

    def enabled(self):
        return True

    def run(self):
        raise NotImplementedError('Command has no implementation')

    def debug(self, text):
        self.api.log.debug('cmd/{}: '.format(self.name, text))

    def info(self, text):
        self.api.log.info('cmd/{}: {}'.format(self.name, text))

    def warn(self, text):
        self.api.log.warn('cmd/{}: {}'.format(self.name, text))

    def error(self, text):
        self.api.log.error('cmd/{}: {}'.format(self.name, text))


class CommandApi:
    core_registry = {}
    plugin_registry = {}

    def __init__(self, api):
        self._api = api
        self._thread = None

    def run(self, cmd):
        if not cmd.enabled():
            self._api.log.info(
                'cmd/{}: not available right now'.format(cmd.name))
            return

        async def run():
            self._api.log.info('cmd/{}: running...'.format(cmd.name))
            start_time = time.time()
            await cmd.run()
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
        if not path.exists():
            return
        for subpath in path.glob('*.py'):
            spec = importlib.util.spec_from_file_location(
                'bubblesub.plugin', subpath)
            if spec is None:
                continue
            spec.loader.exec_module(importlib.util.module_from_spec(spec))


class CoreCommand(BaseCommand):
    def __init_subclass__(cls):
        CommandApi.core_registry[cls.name] = cls


class PluginCommand(BaseCommand):
    def __init_subclass__(cls):
        CommandApi.plugin_registry[cls.name] = cls
