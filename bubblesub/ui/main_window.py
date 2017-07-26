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


SHORTCUTS = {
    'global': [
        ('Ctrl+N', 'file/new'),  # TODO
        ('Ctrl+O', 'file/open'),  # TODO
        ('Ctrl+S', 'file/save'),
        ('Ctrl+Shift+S', 'file/save-as'),  # TODO
        ('Ctrl+Q', 'file/quit'),
        ('Ctrl+G', 'grid/select-line'),  # TODO
        ('Ctrl+Shift+G', 'grid/select-time'),  # TODO
        ('Ctrl+K', 'grid/select-prev-subtitle'),
        ('Ctrl+J', 'grid/select-next-subtitle'),
        ('Ctrl+A', 'grid/select-all'),
        ('Ctrl+Shift+A', 'grid/select-nothing'),
        ('Alt+1', 'video/play-around-sel-start', -500, 0),
        ('Alt+2', 'video/play-around-sel-start', 0, 500),
        ('Alt+3', 'video/play-around-sel-end', -500, 0),
        ('Alt+4', 'video/play-around-sel-end', 0, 500),
        ('Ctrl+R', 'video/play-current-line'),
        ('Ctrl+P', 'video/toggle-pause'),
        ('Ctrl+Z', 'edit/undo'),  # TODO
        ('Ctrl+Y', 'edit/redo'),  # TODO
        ('Alt+C', 'edit/copy'),  # TODO
        ('Ctrl+Return', 'edit/insert-below'),
        ('Ctrl+Delete', 'edit/delete'),
    ],

    'audio': [
        ('Shift+1', 'edit/move-sel-start', -250),
        ('Shift+2', 'edit/move-sel-start', 250),
        ('Shift+3', 'edit/move-sel-end', -250),
        ('Shift+4', 'edit/move-sel-end', 250),
        ('1', 'edit/move-sel-start', -25),
        ('2', 'edit/move-sel-start', 25),
        ('3', 'edit/move-sel-end', -25),
        ('4', 'edit/move-sel-end', 25),
        ('G', 'edit/commit-sel'),
        ('K', 'edit/insert-above'),
        ('J', 'edit/insert-below'),
        ('Shift+K', 'grid/select-prev-subtitle'),
        ('Shift+J', 'grid/select-next-subtitle'),
    ],
}

# TODO: make this configurable
MENU = {
    '&File': [
        # ('New', 'file/new'),  # TODO
        # ('Open', 'file/open'),  # TODO
        ('Save', 'file/save'),
        # ('Save as', 'file/save-as'),  # TODO
        None,
        ('Quit', 'file/quit'),
    ],

    '&Playback': [
        # ('Jump to line', 'grid/select-line'),  # TODO
        # ('Jump to time', 'grid/select-time'),  # TODO
        ('Select previous subtitle', 'grid/select-prev-subtitle'),
        ('Select next subtitle', 'grid/select-next-subtitle'),
        ('Select all subtitles', 'grid/select-all'),
        ('Clear selection', 'grid/select-nothing'),
        None,
        ('Play 500 ms before selection start', 'video/play-around-sel-start', -500, 0),
        ('Play 500 ms after selection start', 'video/play-around-sel-start', 0, 500),
        ('Play 500 ms before selection end', 'video/play-around-sel-end', -500, 0),
        ('Play 500 ms after selection end', 'video/play-around-sel-end', 0, 500),
        ('Play selection', 'video/play-around-sel', 0, 0),
        ('Play current line', 'video/play-current-line'),
        ('Play until end of the file', 'video/unpause'),
        ('Pause playback', 'video/pause'),
        ('Toggle pause', 'video/toggle-pause'),
    ],

    '&Edit': [
        # ('Undo', 'edit/undo'),  # TODO
        # ('Redo', 'edit/redo'),  # TODO
        None,
        # ('Copy to clipboard', 'edit/copy'),  # TODO
        None,
        ('Glue selection start to previous subtitle', 'edit/glue-sel-start'),
        ('Glue selection end to next subtitle', 'edit/glue-sel-end'),
        # ('Shift selected subtitles', 'edit/shift-times'),  # TODO
        ('Shift selection start (-250 ms)', 'edit/move-sel-start', -250),
        ('Shift selection start (+250 ms)', 'edit/move-sel-start', 250),
        ('Shift selection end (-250 ms)', 'edit/move-sel-end', -250),
        ('Shift selection end (+250 ms)', 'edit/move-sel-end', 250),
        ('Shift selection start (-25 ms)', 'edit/move-sel-start', -25),
        ('Shift selection start (+25 ms)', 'edit/move-sel-start', 25),
        ('Shift selection end (-25 ms)', 'edit/move-sel-end', -25),
        ('Shift selection end (+25 ms)', 'edit/move-sel-end', 25),
        ('Commit selection to subtitle', 'edit/commit-sel'),
        None,
        ('Add new subtitle above current line', 'edit/insert-above'),
        ('Add new subtitle below current line', 'edit/insert-below'),
        ('Duplicate selected subtitles', 'edit/duplicate'),
        ('Delete selected subtitles', 'edit/delete'),
        None,
        # ('Split selection as karaoke', 'edit/split-karaoke'),  # TODO
        # ('Split selection as karaoke', 'edit/join-karaoke'),  # TODO
        None,
        # ('Style editor', 'edit/style-editor'),  # TODO
    ],
}


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

        action_map = self._setup_menu()
        self._setup_shortcuts(action_map)

        subs_grid.setFocus()

    def _run_cmd(self, cmd_name, args):
        callback = bubblesub.commands.commands_dict.get(cmd_name, None)
        if not callback:
            bubblesub.ui.util.error('Invalid command name:\n' + cmd_name)
            return
        with bubblesub.util.Benchmark('Executing command {}'.format(cmd_name)) as b:
            callback(self._api, *args)

    def _setup_menu(self):
        action_map = {}
        for name, items in MENU.items():
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

    def _setup_shortcuts(self, action_map):
        for context, items in SHORTCUTS.items():
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
