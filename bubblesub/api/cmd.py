import sys
import bubblesub.util
import importlib.util


class classproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


class BaseCommand:
    def __init__(self, api):
        self.api = api

    @classproperty
    def name(cls):
        raise NotImplementedError('Command has no name')

    def enabled(self):
        return True

    def run(self, *args, **kwargs):
        raise NotImplementedError('Command has no implementation')


class CommandApi:
    core_registry = {}
    plugin_registry = {}

    def __init__(self, api):
        self._api = api

    @staticmethod
    def run(cmd, cmd_args):
        with bubblesub.util.Benchmark('Executing command {}'.format(cmd.name)):
            if cmd.enabled():
                cmd.run(*cmd_args)

    def get(self, name):
        ret = self.plugin_registry.get(name)
        if not ret:
            ret = self.core_registry.get(name)
        if not ret:
            raise KeyError('No command named {}'.format(name))
        try:
            return ret(self._api)
        except:
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
