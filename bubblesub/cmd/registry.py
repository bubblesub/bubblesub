registry = {}


class BaseCommand:
    def __init_subclass__(cls):
        instance = cls()
        registry[instance.name] = instance

    @property
    def name(self):
        raise NotImplementedError('Command has no name')

    def enabled(self, api):
        return True

    def run(self, api, *args, **kwargs):
        raise NotImplementedError('Command has no implementation')


def get(name):
    return registry[name]
