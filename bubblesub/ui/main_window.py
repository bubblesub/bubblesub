from PyQt5 import QtCore
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

        audio = bubblesub.ui.audio.Audio(api)
        video = bubblesub.ui.video.Video(api)
        editor = bubblesub.ui.editor.Editor(api, self)

        editor_box = QtWidgets.QWidget()
        editor_box.setLayout(QtWidgets.QVBoxLayout())
        editor_box.layout().setContentsMargins(0, 0, 0, 0)
        editor_box.layout().addWidget(audio)
        editor_box.layout().addWidget(editor)

        top_bar = QtWidgets.QWidget()
        top_bar.setLayout(QtWidgets.QHBoxLayout())
        top_bar.layout().setContentsMargins(0, 0, 0, 0)
        top_bar.layout().addWidget(video)
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

        video.setSizePolicy(sp_once)
        editor_box.setSizePolicy(sp_twice)
        audio.setSizePolicy(sp_twice)
        editor.setSizePolicy(sp_once)

        subs_grid = bubblesub.ui.subs_grid.SubsGrid(api)

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Vertical)
        splitter.addWidget(top_bar)
        splitter.addWidget(subs_grid)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        self.setCentralWidget(splitter)

        self._setup_menu()

    def _setup_menu(self):
        # TODO: make this configurable
        menu = {
            '&File': [
                # ('New', 'Ctrl+N', 'file/new'),  # TODO
                # ('Open', 'Ctrl+O', 'file/open'),  # TODO
                ('Save', 'Ctrl+S', 'file/save'),
                # ('Save as', 'Ctrl+Shift+S', 'file/save-as'),  # TODO
                None,
                ('Quit', 'Ctrl+Q', 'file/quit'),
            ],

            '&Playback': [
                # ('Jump to line', 'Ctrl+G', 'grid/select-line'),  # TODO
                # ('Jump to time', 'Ctrl+Shift+G', 'grid/select-time'),  # TODO
                ('Select previous subtitle', 'Ctrl+K', 'grid/select-prev-subtitle'),
                ('Select next subtitle', 'Ctrl+J', 'grid/select-next-subtitle'),
                ('Select all subtitles', 'Ctrl+A', 'grid/select-all'),
                ('Clear selection', 'Ctrl+Shift+A', 'grid/select-nothing'),
                None,
                ('Play 500 ms before selection start', 'Alt+1', 'video/play-around-sel-start', -500, 0),
                ('Play 500 ms after selection start', 'Alt+2', 'video/play-around-sel-start', 0, 500),
                ('Play 500 ms before selection end', 'Alt+3', 'video/play-around-sel-end', -500, 0),
                ('Play 500 ms after selection end', 'Alt+4', 'video/play-around-sel-end', 0, 500),
                ('Play selection', None, 'video/play-around-sel', 0, 0),
                ('Play current line', 'Ctrl+R', 'video/play-current-line'),
                ('Play until end of the file', None, 'video/unpause'),
                ('Pause playback', None, 'video/pause'),
                ('Toggle pause', 'Ctrl+P', 'video/toggle-pause'),
            ],

            '&Edit': [
                # ('Undo', 'Ctrl+Z', 'edit/undo'),  # TODO
                # ('Redo', 'Ctrl+Y', 'edit/redo'),  # TODO
                None,
                # ('Copy to clipboard', 'Ctrl+C', 'edit/copy'),  # TODO
                None,
                ('Glue selection start to previous subtitle', None, 'edit/glue-sel-start'),
                ('Glue selection end to next subtitle', None, 'edit/glue-sel-end'),
                # ('Shift selected subtitles', None, 'edit/shift-times'),  # TODO
                ('Shift selection start (-250 ms)', 'Ctrl+1', 'edit/move-sel-start', -250),
                ('Shift selection start (+250 ms)', 'Ctrl+2', 'edit/move-sel-start', 250),
                ('Shift selection end (-250 ms)', 'Ctrl+3', 'edit/move-sel-end', -250),
                ('Shift selection end (+250 ms)', 'Ctrl+4', 'edit/move-sel-end', 250),
                ('Shift selection start (-25 ms)', 'Ctrl+Shift+1', 'edit/move-sel-start', -25),
                ('Shift selection start (+25 ms)', 'Ctrl+Shift+2', 'edit/move-sel-start', 25),
                ('Shift selection end (-25 ms)', 'Ctrl+Shift+3', 'edit/move-sel-end', -25),
                ('Shift selection end (+25 ms)', 'Ctrl+Shift+4', 'edit/move-sel-end', 25),
                ('Commit selection to subtitle', 'Ctrl+G', 'edit/commit-sel'),
                None,
                ('Add new subtitle above current line', None, 'edit/insert-above'),
                ('Add new subtitle below current line', 'Ctrl+Return', 'edit/insert-below'),
                # ('Duplicate selected subtitle', None, 'edit/duplicate'),  # TODO
                # ('Delete selected subtitles', None, 'edit/delete'),  # TODO
                None,
                # ('Split selection as karaoke', None, 'edit/split-karaoke'),  # TODO
                # ('Split selection as karaoke', None, 'edit/join-karaoke'),  # TODO
                None,
                # ('Style editor', None, 'edit/style-editor'),  # TODO
            ],
        }

        def trigger(action):
            command_name, args = action.data()
            callback = bubblesub.commands.commands_dict.get(command_name, None)
            if not callback:
                bubblesub.ui.util.error('Invalid command name:\n' + command_name)
                return
            callback(self._api, *args)

        actions = []
        for name, items in menu.items():
            submenu = self.menuBar().addMenu(name)
            for item in items:
                if item is None:
                    # XXX: only the first call works, what the fuck?
                    actions.append(submenu.addSeparator())
                    continue

                action_name, shortcut, command_name, *args = item
                action = submenu.addAction(action_name)
                action.setData([command_name, args])
                if shortcut:
                    action.setShortcut(shortcut)

            submenu.triggered[QtWidgets.QAction].connect(trigger)

    def closeEvent(self, event):
        # TODO: ask only when necessary
        if bubblesub.ui.util.ask('Are you sure you want to exit the program?'):
            event.accept()
        else:
            event.ignore()
