import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand


VIDEO_FILTER = 'Video filters (*.avi *.mkv *.webm *.mp4);;All files (*.*)'
SUBS_FILTER = 'Advanced Substation Alpha (*.ass)'


def _get_dialog_dir(api):
    if api.subs.path:
        return str(api.subs.path.parent)
    return None


async def _get_save_file_name(api, main_window, filter):
    return bubblesub.ui.util.save_dialog(
        main_window, filter, directory=_get_dialog_dir(api))


async def _get_load_file_name(api, main_window, filter):
    return bubblesub.ui.util.load_dialog(
        main_window, filter, directory=_get_dialog_dir(api))


def _ask_about_unsaved_changes(api):
    if not api.undo.needs_save:
        return True
    return bubblesub.ui.util.ask(
        'There are unsaved changes. '
        'Are you sure you want to close the current file?')


class FileNewCommand(CoreCommand):
    name = 'file/new'
    menu_name = 'New'

    async def run(self):
        if _ask_about_unsaved_changes(self.api):
            self.api.subs.unload()


class FileOpenCommand(CoreCommand):
    name = 'file/open'
    menu_name = 'Open'

    async def run(self):
        if _ask_about_unsaved_changes(self.api):
            path = await self.api.gui.exec(_get_load_file_name, VIDEO_FILTER)
            if not path:
                self.info('opening cancelled.')
            else:
                self.api.subs.load_ass(path)
                self.info('opened {}'.format(path))


class FileLoadVideo(CoreCommand):
    name = 'file/load-video'
    menu_name = 'Load video'

    async def run(self):
        path = await self.api.gui.exec(_get_load_file_name, VIDEO_FILTER)
        if not path:
            self.info('loading video cancelled.')
        else:
            self.api.video.load(path)
            self.info('loading {}'.format(path))


class FileSaveCommand(CoreCommand):
    name = 'file/save'
    menu_name = 'Save'

    async def run(self):
        path = self.api.subs.path
        if not path:
            path = await self.api.gui.exec(_get_save_file_name, SUBS_FILTER)
            if not path:
                self.info('saving cancelled.')
                return
        self.api.subs.save_ass(path, remember_path=True)
        self.info('saved subtitles to {}'.format(path))


class FileSaveAsCommand(CoreCommand):
    name = 'file/save-as'
    menu_name = 'Save as'

    async def run(self):
        path = await self.api.gui.exec(_get_save_file_name, SUBS_FILTER)
        if not path:
            self.info('saving cancelled.')
        else:
            self.api.subs.save_ass(path, remember_path=True)
            self.info('saved subtitles to {}'.format(path))


class FileQuitCommand(CoreCommand):
    name = 'file/quit'
    menu_name = 'Quit'

    async def run(self):
        self.api.gui.quit()
