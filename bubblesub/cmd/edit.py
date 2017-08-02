import bubblesub.ui.util
from bubblesub.cmd.registry import BaseCommand
from PyQt5 import QtWidgets


class EditUndoCommand(BaseCommand):
    name = 'edit/undo'

    def enabled(self, api):
        return api.undo.has_undo

    def run(self, api):
        api.undo.undo()


class EditRedoCommand(BaseCommand):
    name = 'edit/redo'

    def enabled(self, api):
        return api.undo.has_redo

    def run(self, api):
        api.undo.redo()


class EditInsertAboveCommand(BaseCommand):
    name = 'edit/insert-above'

    def run(self, api):
        if not api.subs.selected_indexes:
            idx = 0
            prev_sub = None
            cur_sub = None
        else:
            idx = api.subs.selected_indexes[0]
            prev_sub = api.subs.lines.get(idx - 1)
            cur_sub = api.subs.lines[idx]

        end = (
            cur_sub.start
            if cur_sub
            else api.opt.general['subs']['default_duration'])
        start = end - api.opt.general['subs']['default_duration']
        if start < 0:
            start = 0
        if prev_sub and start < prev_sub.end:
            start = prev_sub.end
        if start > end:
            start = end
        api.subs.lines.insert_one(idx, start=start, end=end, style='Default')
        api.subs.selected_indexes = [idx]


class EditInsertBelowCommand(BaseCommand):
    name = 'edit/insert-below'

    def run(self, api):
        if not api.subs.selected_indexes:
            idx = 0
            cur_sub = None
            next_sub = api.subs.lines.get(0)
        else:
            idx = api.subs.selected_indexes[-1]
            cur_sub = api.subs.lines[idx]
            idx += 1
            next_sub = api.subs.lines.get(idx)

        start = cur_sub.end if cur_sub else 0
        end = start + api.opt.general['subs']['default_duration']
        if next_sub and end > next_sub.start:
            end = next_sub.start
        if end < start:
            end = start
        api.subs.lines.insert_one(idx, start=start, end=end, style='Default')
        api.subs.selected_indexes = [idx]


class EditDuplicateCommand(BaseCommand):
    name = 'edit/duplicate'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        new_selection = []
        api.gui.begin_update()
        for idx in reversed(api.subs.selected_indexes):
            sub = api.subs.lines[idx]
            api.subs.lines.insert_one(
                idx + 1,
                **{k: getattr(sub, k) for k in sub.prop.keys()})
            new_selection.append(
                idx + len(api.subs.selected_indexes) - len(new_selection))
        api.subs.selected_indexes = new_selection
        api.gui.end_update()


class EditDeleteCommand(BaseCommand):
    name = 'edit/delete'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        for idx in reversed(api.subs.selected_indexes):
            api.subs.lines.remove(idx, 1)
        api.subs.selected_indexes = []


class EditSwapTextAndNotesCommand(BaseCommand):
    name = 'edit/swap-text-and-notes'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        for sub in api.subs.selected_lines:
            sub.begin_update()
            sub.text, sub.note = sub.note, sub.text
            sub.end_update()


class EditSplitSubAtVideoCommand(BaseCommand):
    name = 'edit/split-sub-at-video'

    def enabled(self, api):
        return len(api.subs.selected_indexes) == 1

    def run(self, api):
        idx = api.subs.selected_indexes[0]
        sub = api.subs.lines[idx]
        split_pos = api.video.current_pts
        if split_pos < sub.start or split_pos > sub.end:
            return
        api.gui.begin_update()
        api.subs.lines.insert_one(
            idx + 1, **{k: getattr(sub, k) for k in sub.prop.keys()})
        api.subs.lines[idx].end = split_pos
        api.subs.lines[idx + 1].start = split_pos
        api.subs.selected_indexes = [idx, idx + 1]
        api.gui.end_update()


class EditJoinSubsKeepFirstCommand(BaseCommand):
    name = 'edit/join-subs/keep-first'

    def enabled(self, api):
        return len(api.subs.selected_indexes) > 1

    def run(self, api):
        idx = api.subs.selected_indexes[0]
        last_idx = api.subs.selected_indexes[-1]
        api.subs.lines[idx].end = api.subs.lines[last_idx].end
        for i in reversed(api.subs.selected_indexes[1:]):
            api.subs.lines.remove(i, 1)
        api.subs.selected_indexes = [idx]


class EditJoinSubsConcatenateCommand(BaseCommand):
    name = 'edit/join-subs/concatenate'

    def enabled(self, api):
        return len(api.subs.selected_indexes) > 1

    def run(self, api):
        idx = api.subs.selected_indexes[0]
        last_idx = api.subs.selected_indexes[-1]

        sub = api.subs.lines[idx]
        sub.begin_update()
        sub.end = api.subs.lines[last_idx].end

        new_text = ''
        new_note = ''
        for i in reversed(api.subs.selected_indexes[1:]):
            new_text = api.subs.lines[i].text + new_text
            new_note = api.subs.lines[i].note + new_note
            api.subs.lines.remove(i, 1)

        sub.text += new_text
        sub.note += new_note
        sub.end_update()
        api.subs.selected_indexes = [idx]


class EditShiftSubsWithGuiCommand(BaseCommand):
    name = 'edit/shift-subs-with-gui'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        dialog = self.ShiftTimesDialog()
        if dialog.exec_():
            delta = dialog.value()
            for sub in api.subs.selected_lines:
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

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(label)
            layout.addWidget(self.time_widget)
            layout.addWidget(strip)
            self.setLayout(layout)

        def value(self):
            return bubblesub.util.str_to_ms(self.time_widget.text())


class EditSnapSubsStartToVideoCommand(BaseCommand):
    name = 'edit/snap-subs-start-to-video'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        for sub in api.subs.selected_lines:
            sub.start = api.video.current_pts


class EditSnapSubsEndToVideoCommand(BaseCommand):
    name = 'edit/snap-subs-end-to-video'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        for sub in api.subs.selected_lines:
            sub.end = api.video.current_pts


class EditSnapSubsToVideoCommand(BaseCommand):
    name = 'edit/snap-subs-to-video'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        for sub in api.subs.selected_lines:
            sub.start = api.video.current_pts
            sub.end = (
                api.video.current_pts
                + api.opt.general['subs']['default_duration'])


class EditSnapSubsStartToPreviousSubtitleCommand(BaseCommand):
    name = 'edit/snap-subs-start-to-prev-sub'

    def enabled(self, api):
        if not api.subs.has_selection:
            return False
        return api.subs.selected_lines[0].prev_sub is not None

    def run(self, api):
        prev_sub = api.subs.selected_lines[0].prev_sub
        for sub in api.subs.selected_lines:
            sub.start = prev_sub.end


class EditSnapSubsEndToNextSubtitleCommand(BaseCommand):
    name = 'edit/snap-subs-end-to-next-sub'

    def enabled(self, api):
        if not api.subs.has_selection:
            return False
        return api.subs.selected_lines[-1].next_sub is not None

    def run(self, api):
        next_sub = api.subs.selected_lines[-1].next_sub
        for sub in api.subs.selected_lines:
            sub.end = next_sub.start


class EditShiftSubsStartCommand(BaseCommand):
    name = 'edit/shift-subs-start'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api, ms):
        for sub in api.subs.selected_lines:
            sub.start = max(0, sub.start + ms)


class EditShiftSubsEndCommand(BaseCommand):
    name = 'edit/shift-subs-end'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api, ms):
        for sub in api.subs.selected_lines:
            sub.end = max(0, sub.end + ms)


class EditShiftSubsCommand(BaseCommand):
    name = 'edit/shift-subs'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api, ms):
        for sub in api.subs.selected_lines:
            sub.start = max(0, sub.start + ms)
            sub.end = max(0, sub.end + ms)
