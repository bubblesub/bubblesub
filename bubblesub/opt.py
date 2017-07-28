import json


class Serializer:
    def __init__(self, location):
        self._location = location

    @property
    def _hotkeys_path(self):
        return self._location / 'hotkey.json'

    @property
    def _menu_path(self):
        return self._location / 'menu.json'

    @property
    def _general_path(self):
        return self._location / 'general.json'

    def load(self):
        hotkeys = None
        menu = None
        if self._hotkeys_path.exists():
            hotkeys = json.loads(self._hotkeys_path.read_text())
        if self._menu_path.exists():
            menu = json.loads(self._menu_path.read_text())
        if self._general_path.exists():
            general = json.loads(self._general_path.read_text())
        return hotkeys, menu, general

    def write(self, hotkeys, menu, general):
        self._location.mkdir(parents=True, exist_ok=True)
        self._hotkeys_path.write_text(json.dumps(hotkeys, indent=4))
        self._menu_path.write_text(json.dumps(menu, indent=4))
        self._general_path.write_text(json.dumps(general, indent=4))


class Options:
    def __init__(self):
        self.general = {
            'convert_newlines': True,
        }

        self.hotkeys = {
            'global': [
                ('Ctrl+N', 'file/new'),  # TODO
                ('Ctrl+O', 'file/open'),  # TODO
                ('Ctrl+S', 'file/save'),
                ('Ctrl+Shift+S', 'file/save-as'),  # TODO
                ('Ctrl+Q', 'file/quit'),
                ('Ctrl+G', 'grid/jump-to-line'),
                ('Ctrl+Shift+G', 'grid/jump-to-time'),
                ('Ctrl+K', 'grid/select-prev-subtitle'),
                ('Ctrl+J', 'grid/select-next-subtitle'),
                ('Ctrl+A', 'grid/select-all'),
                ('Ctrl+Shift+A', 'grid/select-nothing'),
                ('Alt+1', 'video/play-around-sel-start', -500, 0),
                ('Alt+2', 'video/play-around-sel-start', 0, 500),
                ('Alt+3', 'video/play-around-sel-end', -500, 0),
                ('Alt+4', 'video/play-around-sel-end', 0, 500),
                ('Ctrl+R', 'video/play-around-sel', 0, 0),
                ('Ctrl+,', 'video/step-frame', -1),
                ('Ctrl+.', 'video/step-frame', 1),
                ('Ctrl+Shift+,', 'video/step-frame', -10),
                ('Ctrl+Shift+.', 'video/step-frame', 10),
                ('Ctrl+T', 'video/play-current-line'),
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
                ('A', 'audio/scroll', -1),
                ('F', 'audio/scroll', 1),
                (',', 'video/step-frame', -1),
                ('.', 'video/step-frame', 1),
                ('Shift+,', 'video/step-frame', -10),
                ('Shift+.', 'video/step-frame', 10),
            ],
        }

        self.menu = {
            '&File': [
                # ('New', 'file/new'),  # TODO
                # ('Open', 'file/open'),  # TODO
                ('Save', 'file/save'),
                # ('Save as', 'file/save-as'),  # TODO
                None,
                ('Quit', 'file/quit'),
            ],

            '&Playback': [
                ('Jump to line', 'grid/jump-to-line'),
                ('Jump to time', 'grid/jump-to-time'),
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
                None,
                ('Step 1 frame backward', 'video/step-frame', -1),
                ('Step 1 frame forward', 'video/step-frame', 1),
                ('Step 10 frames backward', 'video/step-frame', -10),
                ('Step 10 frames forward', 'video/step-frame', 10),
                None,
                ('Pause playback', 'video/pause'),
                ('Toggle pause', 'video/toggle-pause'),
                None,
                ('Scroll waveform backward', 'audio/scroll', -1),
                ('Scroll waveform forward', 'audio/scroll', 1),
            ],

            '&Edit': [
                # ('Undo', 'edit/undo'),  # TODO
                # ('Redo', 'edit/redo'),  # TODO
                None,
                # ('Copy to clipboard', 'edit/copy'),  # TODO
                None,
                ('Glue selection start to previous subtitle', 'edit/glue-sel-start'),
                ('Glue selection end to next subtitle', 'edit/glue-sel-end'),
                ('Shift selected subtitles', 'edit/move-subs-with-gui'),
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

    def load(self, location):
        serializer = Serializer(location)
        hotkeys, menu, general = serializer.load()
        if hotkeys:
            self.hotkeys = hotkeys
        if menu:
            self.menu = menu
        if general:
            self.general = general

    def save(self, location):
        serializer = Serializer(location)
        serializer.write(self.hotkeys, self.menu, self.general)
