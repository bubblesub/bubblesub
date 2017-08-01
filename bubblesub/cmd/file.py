import bubblesub.ui.util
from bubblesub.cmd.registry import BaseCommand
from PyQt5 import QtWidgets


def _get_dialog_dir(api):
    if api.subs.path:
        return str(api.subs.path.parent)
    return None


def _ask_about_unsaved_changes(api):
    if not api.undo.needs_save:
        return True
    return bubblesub.ui.util.ask(
        'There are unsaved changes. '
        'Are you sure you want to close the current file?')


class FileNewCommand(BaseCommand):
    name = 'file/new'

    def run(self, api):
        if _ask_about_unsaved_changes(api):
            api.subs.unload()
            api.log.info('Created new subtitles')


class FileOpenCommand(BaseCommand):
    name = 'file/open'

    def run(self, api):
        if _ask_about_unsaved_changes(api):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                api.gui.main_window,
                directory=_get_dialog_dir(api),
                initialFilter='*.ass')
            if not path:
                api.log.info('Opening cancelled.')
            else:
                api.subs.load_ass(path)
                api.log.info('Opened {}'.format(path))


class FileLoadVideo(BaseCommand):
    name = 'file/load-video'

    def run(self, api):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            api.gui.main_window,
            directory=_get_dialog_dir(api),
            initialFilter='*.mkv')
        if not path:
            api.log.info('Loading video cancelled.')
        else:
            api.video.load(path)
            api.log.info('Loading {}'.format(path))


class FileSaveCommand(BaseCommand):
    name = 'file/save'

    def run(self, api):
        path = api.subs.path
        if not api.subs.path:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                api.gui.main_window,
                directory=_get_dialog_dir(api),
                initialFilter='*.ass')
            if not path:
                api.log.info('Saving cancelled.')
                return
        api.subs.save_ass(path, remember_path=True)
        api.log.info('Saved subtitles to {}'.format(path))


class FileSaveAsCommand(BaseCommand):
    name = 'file/save-as'

    def run(self, api):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            api.gui.main_window,
            directory=_get_dialog_dir(api),
            initialFilter='*.ass')
        if not path:
            api.log.info('Saving cancelled.')
        else:
            api.subs.save_ass(path, remember_path=True)
            api.log.info('Saved subtitles to {}'.format(path))


class FileQuitCommand(BaseCommand):
    name = 'file/quit'

    def run(self, api):
        api.gui.quit()
