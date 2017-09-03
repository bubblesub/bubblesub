from bubblesub.api.cmd import CoreCommand


class ResetPluginsCommand(CoreCommand):
    name = 'misc/reload-plugins'
    menu_name = 'Reload plugins'

    def __init__(self, api):
        super().__init__(api)

    async def run(self):
        if self.api.opt.location:
            self.api.cmd.load_plugins(self.api.opt.location / 'scripts')
