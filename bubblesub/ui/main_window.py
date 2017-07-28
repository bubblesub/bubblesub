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

        editor_box = QtWidgets.QWidget()
        editor_box.setLayout(QtWidgets.QVBoxLayout())
        editor_box.layout().setContentsMargins(0, 0, 0, 0)
        editor_box.layout().addWidget(self._audio)
        editor_box.layout().addWidget(self._editor)

        top_bar = QtWidgets.QWidget()
        top_bar.setLayout(QtWidgets.QHBoxLayout())
        top_bar.layout().setContentsMargins(0, 0, 0, 0)
        top_bar.layout().addWidget(self._video)
        top_bar.layout().addWidget(editor_box)

        # TODO: console with logs
        # TODO: replace layouts with splitters
        # TODO: remember position of splitters in a config file

        sp_once = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sp_once.setHorizontalStretch(1)
        sp_once.setVerticalStretch(1)
        sp_twice = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sp_twice.setHorizontalStretch(2)
        sp_twice.setVerticalStretch(2)

        editor_box.setSizePolicy(sp_twice)
        self._video.setSizePolicy(sp_once)
        self._audio.setSizePolicy(sp_twice)
        self._editor.setSizePolicy(sp_once)

        subs_grid = bubblesub.ui.subs_grid.SubsGrid(api)

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Vertical)
        splitter.addWidget(top_bar)
        splitter.addWidget(subs_grid)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        self.setCentralWidget(splitter)

        action_map = self._setup_menu(api.opt)
        self._setup_hotkeys(api.opt, action_map)

        subs_grid.setFocus()

    def _run_cmd(self, cmd_name, args):
        cmd = bubblesub.commands.registry.get(cmd_name, None)
        if not cmd:
            bubblesub.ui.util.error('Invalid command name:\n' + cmd_name)
            return
        with bubblesub.util.Benchmark('Executing command {}'.format(cmd_name)):
            cmd.run(self._api, *args)

    def _setup_menu(self, opt):
        action_map = {}
        for name, items in opt.menu.items():
            submenu = self.menuBar().addMenu(name)
            for item in items:
                if item is None:
                    submenu.addSeparator()
                    continue
                action_name, cmd_name, *args = item
                action = submenu.addAction(action_name)
                action.triggered.connect(
                    functools.partial(self._run_cmd, cmd_name, args))
                action_map[(cmd_name, *args)] = action
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
                    functools.partial(self._run_cmd, cmd_name, args))
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
