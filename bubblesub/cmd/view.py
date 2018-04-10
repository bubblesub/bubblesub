from PyQt5 import QtWidgets

import bubblesub.api
from bubblesub.api.cmd import CoreCommand


class ViewSetPaletteCommand(CoreCommand):
    name = 'view/set-palette'

    def __init__(self, api: bubblesub.api.Api, palette_name: str) -> None:
        super().__init__(api)
        self._palette_name = palette_name

    @property
    def menu_name(self) -> str:
        return '&Switch to {} color scheme'.format(self._palette_name)

    async def run(self) -> None:
        async def run(
                api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow,
        ) -> None:
            api.opt.general['current_palette'] = self._palette_name
            main_window.apply_palette(self._palette_name)

        await self.api.gui.exec(run)


class ViewFocusTextEditorCommand(CoreCommand):
    name = 'view/focus-text-editor'
    menu_name = '&Focus text editor'

    async def run(self) -> None:
        async def run(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow,
        ) -> None:
            main_window.editor.center.text_edit.setFocus()
            main_window.editor.center.text_edit.selectAll()

        await self.api.gui.exec(run)


class ViewFocusNoteEditorCommand(CoreCommand):
    name = 'view/focus-note-editor'
    menu_name = '&Focus note editor'

    async def run(self) -> None:
        async def run(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow,
        ) -> None:
            main_window.editor.center.note_edit.setFocus()
            main_window.editor.center.note_edit.selectAll()

        await self.api.gui.exec(run)


class ViewFocusGridCommand(CoreCommand):
    name = 'view/focus-grid'
    menu_name = '&Focus subtitles grid'

    async def run(self) -> None:
        async def run(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow,
        ) -> None:
            main_window.subs_grid.setFocus()

        await self.api.gui.exec(run)


class ViewFocusSpectrogramCommand(CoreCommand):
    name = 'view/focus-spectrogram'
    menu_name = '&Focus spectrogram'

    async def run(self) -> None:
        async def run(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow,
        ) -> None:
            main_window.audio.setFocus()

        await self.api.gui.exec(run)
