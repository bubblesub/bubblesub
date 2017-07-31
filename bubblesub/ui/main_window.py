import functools
import base64
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


def _load_splitter_state(widget, data):
    widget.restoreState(base64.b64decode(data))


def _get_splitter_state(widget):
    return base64.b64encode(widget.saveState()).decode('ascii')


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

        self._video = bubblesub.ui.video.Video(api, self)
        self._audio = bubblesub.ui.audio.Audio(api, self)
        self._editor = bubblesub.ui.editor.Editor(api, self)
        self._subs_grid = bubblesub.ui.subs_grid.SubsGrid(api)

        self._editor_splitter = QtWidgets.QSplitter(self)
        self._editor_splitter.setOrientation(QtCore.Qt.Vertical)
        self._editor_splitter.addWidget(self._audio)
        self._editor_splitter.addWidget(self._editor)

        self._top_bar = QtWidgets.QSplitter(self)
        self._top_bar.setOrientation(QtCore.Qt.Horizontal)
        self._top_bar.addWidget(self._video)
        self._top_bar.addWidget(self._editor_splitter)

        # TODO: console with logs

        self._main_splitter = QtWidgets.QSplitter(self)
        self._main_splitter.setOrientation(QtCore.Qt.Vertical)
        self._main_splitter.addWidget(self._top_bar)
        self._main_splitter.addWidget(self._subs_grid)
        self._main_splitter.setContentsMargins(8, 8, 8, 8)
        self.setCentralWidget(self._main_splitter)

        action_map = self._setup_menu(api.opt)
        self._setup_hotkeys(api.opt, action_map)

        self._top_bar.setStretchFactor(0, 1)
        self._top_bar.setStretchFactor(1, 2)
        self._main_splitter.setStretchFactor(0, 1)
        self._main_splitter.setStretchFactor(1, 5)

        self._subs_grid.setFocus()
        self._restore_splitters()

    def _setup_menu(self, opt):
        action_map = {}
        self._setup_submenu(self.menuBar(), self._api.opt.menu, action_map)
        return action_map

    def _setup_submenu(self, parent, menu_def, action_map):
        for item in menu_def:
            if item is None:
                parent.addSeparator()
            elif isinstance(item[1], list):
                submenu = parent.addMenu(item[0])
                submenu.aboutToShow.connect(
                    functools.partial(self._menu_about_to_show, submenu))
                self._setup_submenu(submenu, item[1], action_map)
            else:
                action_name, cmd_name, *cmd_args = item
                action = CommandAction(self._api, cmd_name, cmd_args)
                action.setParent(parent)
                action.setText(action_name)
                parent.addAction(action)
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
        self._store_splitters()
        if self._api.undo.needs_save and not bubblesub.ui.util.ask(
                'There are unsaved changes. '
                'Are you sure you want to exit the program?'):
            event.ignore()
        else:
            event.accept()

    def _restore_splitters(self):
        splitter_cfg = self._api.opt.general.get('splitters', None)
        if not splitter_cfg:
            return
        _load_splitter_state(self._top_bar, splitter_cfg['top'])
        _load_splitter_state(self._editor_splitter, splitter_cfg['editor'])
        _load_splitter_state(self._main_splitter, splitter_cfg['main'])

    def _store_splitters(self):
        self._api.opt.general['splitters'] = {
            'top': _get_splitter_state(self._top_bar),
            'editor': _get_splitter_state(self._editor_splitter),
            'main': _get_splitter_state(self._main_splitter),
        }

    def _menu_about_to_show(self, menu):
        for action in menu.actions():
            if hasattr(action, 'cmd') and action.cmd:
                action.setEnabled(action.cmd.enabled(action.api))
