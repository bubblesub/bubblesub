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


class ViewFocusTextEditorCommand(CoreCommand):
    name = 'view/focus-text-editor'
    menu_name = 'Focus text editor'

    async def run(self):
        async def run(_api, main_window):
            main_window.editor.text_edit.setFocus()

        await self.api.gui.exec(run)


class ViewFocusNoteEditorCommand(CoreCommand):
    name = 'view/focus-note-editor'
    menu_name = 'Focus note editor'

    async def run(self):
        async def run(_api, main_window):
            main_window.editor.note_edit.setFocus()

        await self.api.gui.exec(run)


class ViewFocusGridCommand(CoreCommand):
    name = 'view/focus-grid'
    menu_name = 'Focus subtitles grid'

    async def run(self):
        async def run(_api, main_window):
            main_window.subs_grid.setFocus()

        await self.api.gui.exec(run)


class ViewFocusSpectrogramCommand(CoreCommand):
    name = 'view/focus-spectrogram'
    menu_name = 'Focus spectrogram'

    async def run(self):
        async def run(_api, main_window):
            main_window.audio.setFocus()

        await self.api.gui.exec(run)
