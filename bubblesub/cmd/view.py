from bubblesub.api.cmd import CoreCommand


class ViewSetPaletteCommand(CoreCommand):
    name = 'view/set-palette'

    def __init__(self, api, palette_name):
        super().__init__(api)
        self._palette_name = palette_name

    @property
    def menu_name(self):
        return 'Switch to {} color scheme'.format(self._palette_name)

    async def run(self):
        async def run(api, main_window):
            api.opt.general['current_palette'] = self._palette_name
            main_window.apply_palette(self._palette_name)

        await self.api.gui.exec(run)
