import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand
from PyQt5 import QtWidgets


class EditUndoCommand(CoreCommand):
    name = 'edit/undo'
    menu_name = 'Undo'

    def enabled(self):
        return self.api.undo.has_undo

    async def run(self):
        self.api.undo.undo()


class EditRedoCommand(CoreCommand):
    name = 'edit/redo'
    menu_name = 'Redo'

    def enabled(self):
        return self.api.undo.has_redo

    async def run(self):
        self.api.undo.redo()


class EditInsertAboveCommand(CoreCommand):
    name = 'edit/insert-above'
    menu_name = 'Insert subtitle (above)'

    async def run(self):
        if not self.api.subs.selected_indexes:
            idx = 0
            prev_sub = None
            cur_sub = None
        else:
            idx = self.api.subs.selected_indexes[0]
            prev_sub = self.api.subs.lines.get(idx - 1)
            cur_sub = self.api.subs.lines[idx]

        end = (
            cur_sub.start
            if cur_sub
            else self.api.opt.general['subs']['default_duration'])
        start = end - self.api.opt.general['subs']['default_duration']
        if start < 0:
            start = 0
        if prev_sub and start < prev_sub.end:
            start = prev_sub.end
        if start > end:
            start = end
        self.api.subs.lines.insert_one(
            idx, start=start, end=end, style='Default')
        self.api.subs.selected_indexes = [idx]


class EditInsertBelowCommand(CoreCommand):
    name = 'edit/insert-below'
    menu_name = 'Insert subtitle (below)'

    async def run(self):
        if not self.api.subs.selected_indexes:
            idx = 0
            cur_sub = None
            next_sub = self.api.subs.lines.get(0)
        else:
            idx = self.api.subs.selected_indexes[-1]
            cur_sub = self.api.subs.lines[idx]
            idx += 1
            next_sub = self.api.subs.lines.get(idx)

        start = cur_sub.end if cur_sub else 0
        end = start + self.api.opt.general['subs']['default_duration']
        if next_sub and end > next_sub.start:
            end = next_sub.start
        if end < start:
            end = start
        self.api.subs.lines.insert_one(
            idx, start=start, end=end, style='Default')
        self.api.subs.selected_indexes = [idx]


class EditDuplicateCommand(CoreCommand):
    name = 'edit/duplicate'
    menu_name = 'Duplicate selected subtitles'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        self.api.gui.begin_update()
        with self.api.undo.bulk():
            new_selection = []
            for idx in reversed(self.api.subs.selected_indexes):
                sub = self.api.subs.lines[idx]
                self.api.subs.lines.insert_one(
                    idx + 1,
                    **{k: getattr(sub, k) for k in sub.prop.keys()})
                new_selection.append(
                    idx
                    + len(self.api.subs.selected_indexes)
                    - len(new_selection))
            self.api.subs.selected_indexes = new_selection
        self.api.gui.end_update()


class EditDeleteCommand(CoreCommand):
    name = 'edit/delete'
    menu_name = 'Delete selected subtitles'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        with self.api.undo.bulk():
            for idx in reversed(self.api.subs.selected_indexes):
                self.api.subs.lines.remove(idx, 1)
            self.api.subs.selected_indexes = []


class EditSwapTextAndNotesCommand(CoreCommand):
    name = 'edit/swap-text-and-notes'
    menu_name = 'Swap notes with subtitle text'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        with self.api.undo.bulk():
            for sub in self.api.subs.selected_lines:
                sub.begin_update()
                sub.text, sub.note = sub.note, sub.text
                sub.end_update()


class EditSplitSubAtVideoCommand(CoreCommand):
    name = 'edit/split-sub-at-video'
    menu_name = 'Split selected subtitle at video frame'

    def enabled(self):
        return len(self.api.subs.selected_indexes) == 1

    async def run(self):
        with self.api.undo.bulk():
            idx = self.api.subs.selected_indexes[0]
            sub = self.api.subs.lines[idx]
            split_pos = self.api.video.current_pts
            if split_pos < sub.start or split_pos > sub.end:
                return
            self.api.gui.begin_update()
            self.api.subs.lines.insert_one(
                idx + 1, **{k: getattr(sub, k) for k in sub.prop.keys()})
            self.api.subs.lines[idx].end = split_pos
            self.api.subs.lines[idx + 1].start = split_pos
            self.api.subs.selected_indexes = [idx, idx + 1]
            self.api.gui.end_update()


class EditJoinSubsKeepFirstCommand(CoreCommand):
    name = 'edit/join-subs/keep-first'
    menu_name = 'Join subtitles (keep first)'

    def enabled(self):
        return len(self.api.subs.selected_indexes) > 1

    async def run(self):
        with self.api.undo.bulk():
            idx = self.api.subs.selected_indexes[0]
            last_idx = self.api.subs.selected_indexes[-1]
            self.api.subs.lines[idx].end = self.api.subs.lines[last_idx].end
            for i in reversed(self.api.subs.selected_indexes[1:]):
                self.api.subs.lines.remove(i, 1)
            self.api.subs.selected_indexes = [idx]


class EditJoinSubsConcatenateCommand(CoreCommand):
    name = 'edit/join-subs/concatenate'
    menu_name = 'Join subtitles (concatenate)'

    def enabled(self):
        return len(self.api.subs.selected_indexes) > 1

    async def run(self):
        with self.api.undo.bulk():
            idx = self.api.subs.selected_indexes[0]
            last_idx = self.api.subs.selected_indexes[-1]

            sub = self.api.subs.lines[idx]
            sub.begin_update()
            sub.end = self.api.subs.lines[last_idx].end

            new_text = ''
            new_note = ''
            for i in reversed(self.api.subs.selected_indexes[1:]):
                new_text = self.api.subs.lines[i].text + new_text
                new_note = self.api.subs.lines[i].note + new_note
                self.api.subs.lines.remove(i, 1)

            sub.text += new_text
            sub.note += new_note
            sub.end_update()

            self.api.subs.selected_indexes = [idx]


class EditShiftSubsWithGuiCommand(CoreCommand):
    name = 'edit/shift-subs-with-gui'
    menu_name = 'Shift times...'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        dialog = self.ShiftTimesDialog()
        if dialog.exec_():
            delta = dialog.value()

            with self.api.undo.bulk():
                for sub in self.api.subs.selected_lines:
                    sub.begin_update()
                    sub.start += delta
                    sub.end += delta
                    sub.end_update()

    class ShiftTimesDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.time_widget = bubblesub.ui.util.TimeEdit(
                self, allow_negative=True)

            label = QtWidgets.QLabel('Time to add:')
            strip = QtWidgets.QDialogButtonBox(self)
            strip.addButton(strip.Ok)
            strip.addButton(strip.Cancel)
            strip.accepted.connect(self.accept)
            strip.rejected.connect(self.reject)

            layout = QtWidgets.QVBoxLayout(self)
            layout.addWidget(label)
            layout.addWidget(self.time_widget)
            layout.addWidget(strip)

        def value(self):
            return bubblesub.util.str_to_ms(self.time_widget.text())


class EditSnapSubsStartToVideoCommand(CoreCommand):
    name = 'edit/snap-subs-start-to-video'
    menu_name = 'Snap subtitles start to video'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        with self.api.undo.bulk():
            for sub in self.api.subs.selected_lines:
                sub.start = self.api.video.current_pts


class EditSnapSubsEndToVideoCommand(CoreCommand):
    name = 'edit/snap-subs-end-to-video'
    menu_name = 'Snap subtitles end to video'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        with self.api.undo.bulk():
            for sub in self.api.subs.selected_lines:
                sub.end = self.api.video.current_pts


class EditSnapSubsToVideoCommand(CoreCommand):
    name = 'edit/snap-subs-to-video'
    menu_name = 'Snap subtitles to video'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        with self.api.undo.bulk():
            for sub in self.api.subs.selected_lines:
                sub.start = self.api.video.current_pts
                sub.end = (
                    self.api.video.current_pts
                    + self.api.opt.general['subs']['default_duration'])


class EditSnapSubsStartToPreviousSubtitleCommand(CoreCommand):
    name = 'edit/snap-subs-start-to-prev-sub'
    menu_name = 'Snap subtitles start to previous subtitle'

    def enabled(self):
        if not self.api.subs.has_selection:
            return False
        return self.api.subs.selected_lines[0].prev is not None

    async def run(self):
        prev_sub = self.api.subs.selected_lines[0].prev
        with self.api.undo.bulk():
            for sub in self.api.subs.selected_lines:
                sub.start = prev_sub.end


class EditSnapSubsEndToNextSubtitleCommand(CoreCommand):
    name = 'edit/snap-subs-end-to-next-sub'
    menu_name = 'Snap subtitles end to next subtitle'

    def enabled(self):
        if not self.api.subs.has_selection:
            return False
        return self.api.subs.selected_lines[-1].next is not None

    async def run(self):
        next_sub = self.api.subs.selected_lines[-1].next
        with self.api.undo.bulk():
            for sub in self.api.subs.selected_lines:
                sub.end = next_sub.start


class EditShiftSubsStartCommand(CoreCommand):
    name = 'edit/shift-subs-start'

    def __init__(self, api, ms):
        super().__init__(api)
        self._ms = ms

    @property
    def menu_name(self):
        return 'Shift subtitles start ({:+})'.format(self._ms)

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        with self.api.undo.bulk():
            for sub in self.api.subs.selected_lines:
                sub.start = max(0, sub.start + self._ms)


class EditShiftSubsEndCommand(CoreCommand):
    name = 'edit/shift-subs-end'

    def __init__(self, api, ms):
        super().__init__(api)
        self._ms = ms

    @property
    def menu_name(self):
        return 'Shift subtitles end ({:+})'.format(self._ms)

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        with self.api.undo.bulk():
            for sub in self.api.subs.selected_lines:
                sub.end = max(0, sub.end + self._ms)


class EditShiftSubsCommand(CoreCommand):
    name = 'edit/shift-subs'

    def __init__(self, api, ms):
        super().__init__(api)
        self._ms = ms

    @property
    def menu_name(self):
        return 'Shift subtitles end ({:+})'.format(self._ms)

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        with self.api.undo.bulk():
            for sub in self.api.subs.selected_lines:
                sub.start = max(0, sub.start + self._ms)
                sub.end = max(0, sub.end + self._ms)
