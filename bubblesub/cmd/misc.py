from bubblesub.api.cmd import CoreCommand


class ResetPluginsCommand(CoreCommand):
    name = 'misc/reload-plugins'
    menu_name = 'Reload plugins'

    async def run(self) -> None:
        if self.api.opt.root_dir:
            self.api.cmd.load_plugins(self.api.opt.root_dir / 'scripts')
