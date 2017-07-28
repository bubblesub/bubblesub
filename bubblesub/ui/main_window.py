import functools
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
import bubblesub.commands
import bubblesub.ui.editor
import bubblesub.ui.subs_grid
import bubblesub.ui.util
import bubblesub.ui.audio
import bubblesub.ui.video


def _run_cmd(api, cmd_name, args):
    cmd = bubblesub.commands.registry.get(cmd_name, None)
    if not cmd:
        bubblesub.ui.util.error('Invalid command name:\n' + cmd_name)
        return
    with bubblesub.util.Benchmark('Executing command {}'.format(cmd_name)):
        if cmd.enabled(api):
            cmd.run(api, *args)


class CommandAction(QtWidgets.QAction):
    def __init__(self, api, cmd_name, cmd_args):
        super().__init__()
        self.api = api
        self.cmd_name = cmd_name
        self.cmd = bubblesub.commands.registry.get(cmd_name, None)
        self.triggered.connect(
            functools.partial(_run_cmd, api, cmd_name, cmd_args))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, api):
        super().__init__()
        self._api = api

        api.gui.quit_requested.connect(self.close)
        api.gui.begin_update_requested.connect(
            lambda: self.setUpdatesEnabled(False))
        api.gui.end_update_requested.connect(
            lambda: self.setUpdatesEnabled(True))

        self._audio = bubblesub.ui.audio.Audio(api)
        self._video = bubblesub.ui.video.Video(api)
        self._editor = bubblesub.ui.editor.Editor(api, self)
        self._subs_grid = bubblesub.ui.subs_grid.SubsGrid(api)

        editor_splitter = QtWidgets.QSplitter(self)
        editor_splitter.setOrientation(QtCore.Qt.Vertical)
        editor_splitter.addWidget(self._audio)
        editor_splitter.addWidget(self._editor)

        top_bar = QtWidgets.QSplitter(self)
        top_bar.setOrientation(QtCore.Qt.Horizontal)
        top_bar.addWidget(self._video)
        top_bar.addWidget(editor_splitter)

        # TODO: console with logs
        # TODO: remember position of splitters in a config file

        main_splitter = QtWidgets.QSplitter(self)
        main_splitter.setOrientation(QtCore.Qt.Vertical)
        main_splitter.addWidget(top_bar)
        main_splitter.addWidget(self._subs_grid)
        self.setCentralWidget(main_splitter)

        action_map = self._setup_menu(api.opt)
        self._setup_hotkeys(api.opt, action_map)

        top_bar.setStretchFactor(0, 1)
        top_bar.setStretchFactor(1, 2)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 5)

        self._subs_grid.setFocus()

    def _setup_menu(self, opt):
        action_map = {}
        for name, items in opt.menu.items():
            submenu = self.menuBar().addMenu(name)
            for item in items:
                if item is None:
                    submenu.addSeparator()
                    continue

                action_name, cmd_name, *cmd_args = item
                action = CommandAction(self._api, cmd_name, cmd_args)
                action.setParent(submenu)
                action.setText(action_name)
                submenu.addAction(action)
                submenu.aboutToShow.connect(
                    functools.partial(self._menu_about_to_show, submenu))
                action_map[(cmd_name, *cmd_args)] = action
        return action_map

    def _setup_hotkeys(self, opt, action_map):
        for context, items in opt.hotkeys.items():
            for item in items:
                keys, cmd_name, *args = item

                action = action_map.get((cmd_name, *args))
                if action and context == 'global':
                    action.setShortcut(QtGui.QKeySequence(keys))
                    continue

                shortcut = QtWidgets.QShortcut(
                    QtGui.QKeySequence(keys), self)
                shortcut.activated.connect(
                    functools.partial(_run_cmd, self._api, cmd_name, args))
                if context == 'global':
                    shortcut.setContext(QtCore.Qt.ApplicationShortcut)
                elif context == 'audio':
                    shortcut.setParent(self._audio)
                    shortcut.setContext(
                        QtCore.Qt.WidgetWithChildrenShortcut)
                else:
                    raise RuntimeError('Invalid shortcut context')

    def closeEvent(self, event):
        # TODO: ask only when necessary
        if bubblesub.ui.util.ask('Are you sure you want to exit the program?'):
            event.accept()
        else:
            event.ignore()

    def _menu_about_to_show(self, menu):
        for action in menu.actions():
            if hasattr(action, 'cmd') and action.cmd:
                action.setEnabled(action.cmd.enabled(action.api))
