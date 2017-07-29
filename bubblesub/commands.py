import bisect
import bubblesub.ui.util
from PyQt5 import QtWidgets


registry = {}
DEFAULT_SUB_DURATION = 2000  # TODO: move this to config


class BaseCommand:
    def __init_subclass__(cls):
        global registry
        instance = cls()
        registry[instance.name] = instance

    @property
    def name(self):
        raise NotImplementedError('Command has no name')

    def enabled(self, api):
        return True

    def run(self, api, *args, **kwargs):
        raise NotImplementedError('Command has no implementation')


def _ask_about_unsaved_changes(api):
    if not api.undo.has_undo:
        return True
    return bubblesub.ui.util.ask(
        'There are unsaved changes. '
        'Are you sure you want to close the current file?')


class FileSaveCommand(BaseCommand):
    name = 'file/save'

    def run(self, api):
        api.subs.save_ass(api.subs.path)
        # TODO: log in console


class FileQuitCommand(BaseCommand):
    name = 'file/quit'

    def run(self, api):
        api.gui.quit()


class AudioScrollCommand(BaseCommand):
    name = 'audio/scroll'

    def run(self, api, delta):
        distance = delta * api.audio.view_size * 0.05
        api.audio.move_view(distance)


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
        if not api.subs.selected_lines:
            idx = 0
            prev_sub = None
            cur_sub = None
        else:
            idx = api.subs.selected_lines[0]
            prev_sub = api.subs.lines.get(idx - 1)
            cur_sub = api.subs.lines[idx]

        end = cur_sub.start if cur_sub else DEFAULT_SUB_DURATION
        start = end - DEFAULT_SUB_DURATION
        if start < 0:
            start = 0
        if prev_sub and start < prev_sub.end:
            start = prev_sub.end
        if start > end:
            start = end
        api.subs.lines.insert_one(idx, start=start, end=end, style='Default')
        api.subs.selected_lines = [idx]


class EditInsertBelowCommand(BaseCommand):
    name = 'edit/insert-below'

    def run(self, api):
        if not api.subs.selected_lines:
            idx = 0
            cur_sub = None
            next_sub = api.subs.lines.get(0)
        else:
            idx = api.subs.selected_lines[-1]
            cur_sub = api.subs.lines[idx]
            idx += 1
            next_sub = api.subs.lines.get(idx)

        start = cur_sub.end if cur_sub else 0
        end = start + DEFAULT_SUB_DURATION
        if next_sub and end > next_sub.start:
            end = next_sub.start
        if end < start:
            end = start
        api.subs.lines.insert_one(idx, start=start, end=end, style='Default')
        api.subs.selected_lines = [idx]


class EditDuplicateCommand(BaseCommand):
    name = 'edit/duplicate'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        new_selection = []
        api.gui.begin_update()
        for idx in reversed(sorted(api.subs.selected_lines)):
            sub = api.subs.lines[idx]
            api.subs.lines.insert_one(
                idx + 1,
                start=sub.start,
                end=sub.end,
                actor=sub.actor,
                style=sub.style,
                text=sub.text)
            new_selection.append(
                idx + len(api.subs.selected_lines) - len(new_selection))
        api.subs.selected_lines = new_selection
        api.gui.end_update()


class EditDeleteCommand(BaseCommand):
    name = 'edit/delete'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        for idx in reversed(sorted(api.subs.selected_lines)):
            api.subs.lines.remove(idx, 1)
        api.subs.selected_lines = []


class EditGlueSelectionStartCommand(BaseCommand):
    name = 'edit/glue-sel-start'

    def enabled(self, api):
        if not api.audio.has_selection:
            return False
        if not api.subs.selected_lines:
            return False
        return api.subs.selected_lines[0] > 0

    def run(self, api):
        api.audio.select(
            api.subs.lines[api.subs.selected_lines[0] - 1].end,
            api.audio.selection_end)


class EditSnapSelectionStartToVideoCommand(BaseCommand):
    name = 'edit/snap-sel-start-to-video'

    def enabled(self, api):
        return api.audio.has_selection and api.subs.has_selection

    def run(self, api):
        api.audio.select(api.video.current_pts, api.audio.selection_end)


class EditSnapSelectionEndToVideoCommand(BaseCommand):
    name = 'edit/snap-sel-end-to-video'

    def enabled(self, api):
        return api.audio.has_selection and api.subs.has_selection

    def run(self, api):
        api.audio.select(api.audio.selection_start, api.video.current_pts)


class EditRealignSelectionToVideoCommand(BaseCommand):
    name = 'edit/realign-sel-to-video'

    def enabled(self, api):
        return api.audio.has_selection and api.subs.has_selection

    def run(self, api):
        api.audio.select(
            api.video.current_pts,
            api.video.current_pts + DEFAULT_SUB_DURATION)


class EditGlueSelectionEndCommand(BaseCommand):
    name = 'edit/glue-sel-end'

    def enabled(self, api):
        if not api.audio.has_selection:
            return False
        if not api.subs.selected_lines:
            return False
        return api.subs.selected_lines[-1] + 1 < len(api.subs.lines)

    def run(self, api):
        api.audio.select(
            api.audio.selection_start,
            api.subs.lines[api.subs.selected_lines[-1] + 1].start)


class MoveSubsWithGuiCommand(BaseCommand):
    name = 'edit/move-subs-with-gui'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        dialog = self.ShiftTimesDialog()
        if dialog.exec_():
            delta = dialog.result()
            for i in api.subs.selected_lines:
                api.subs.lines[i].begin_update()
                api.subs.lines[i].start += delta
                api.subs.lines[i].end += delta
                api.subs.lines[i].end_update()

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

        def ok_clicked(self):
            self.close()

        def cancel_clicked(self):
            self.close()

        def result(self):
            return bubblesub.util.str_to_ms(self.time_widget.text())


class EditMoveSelectionStartCommand(BaseCommand):
    name = 'edit/move-sel-start'

    def enabled(self, api):
        return api.audio.has_selection

    def run(self, api, ms):
        api.audio.select(
            min(api.audio.selection_end, api.audio.selection_start + ms),
            api.audio.selection_end)


class EditMoveSelectionEndCommand(BaseCommand):
    name = 'edit/move-sel-end'

    def enabled(self, api):
        return api.audio.has_selection

    def run(self, api, ms):
        api.audio.select(
            api.audio.selection_start,
            max(api.audio.selection_start, api.audio.selection_end + ms))


class EditCommitSelectionCommand(BaseCommand):
    name = 'edit/commit-sel'

    def enabled(self, api):
        return api.subs.has_selection and api.audio.has_selection

    def run(self, api):
        for idx in api.subs.selected_lines:
            subtitle = api.subs.lines[idx]
            subtitle.begin_update()
            subtitle.start = api.audio.selection_start
            subtitle.end = api.audio.selection_end
            subtitle.end_update()


class GridJumpToLineCommand(BaseCommand):
    name = 'grid/jump-to-line'

    def enabled(self, api):
        return len(api.subs.lines) > 0

    def run(self, api):
        dialog = QtWidgets.QInputDialog(api.gui.main_window)
        dialog.setLabelText('Line number to jump to:')
        dialog.setIntMinimum(1)
        dialog.setIntMaximum(len(api.subs.lines))
        dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
        if dialog.exec_():
            api.subs.selected_lines = [dialog.intValue() - 1]


class GridJumpToTimeCommand(BaseCommand):
    name = 'grid/jump-to-time'

    def enabled(self, api):
        return len(api.subs.lines) > 0

    def run(self, api):
        dialog = self.JumpToTimeDialog()
        if dialog.exec_():
            target_pts = dialog.result()
            best_distance = None
            best_idx = None
            for i, sub in enumerate(api.subs.lines):
                center = (sub.start + sub.end) / 2
                distance = abs(target_pts - center)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_idx = i
            if best_idx is not None:
                api.subs.selected_lines = [best_idx]

    class JumpToTimeDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.time_widget = bubblesub.ui.util.TimeEdit(
                self, allow_negative=False)

            label = QtWidgets.QLabel('Time to jump to:')
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

        def ok_clicked(self):
            self.close()

        def cancel_clicked(self):
            self.close()

        def result(self):
            return bubblesub.util.str_to_ms(self.time_widget.text())


class GridSelectPrevSubtitleCommand(BaseCommand):
    name = 'grid/select-prev-subtitle'

    def enabled(self, api):
        return len(api.subs.lines) > 0

    def run(self, api):
        if not api.subs.selected_lines:
            api.subs.selected_lines = [len(api.subs.lines) - 1, 0]
        else:
            api.subs.selected_lines = [max(0, api.subs.selected_lines[0] - 1)]


class GridSelectNextSubtitleCommand(BaseCommand):
    name = 'grid/select-next-subtitle'

    def enabled(self, api):
        return len(api.subs.lines) > 0

    def run(self, api):
        if not api.subs.selected_lines:
            api.subs.selected_lines = [0]
        else:
            api.subs.selected_lines = [
                min(api.subs.selected_lines[0] + 1, len(api.subs.lines) - 1)]


class GridSelectAllCommand(BaseCommand):
    name = 'grid/select-all'

    def enabled(self, api):
        return len(api.subs.lines) > 0

    def run(self, api):
        api.subs.selected_lines = list(range(len(api.subs.lines)))


class GridSelectNothingCommand(BaseCommand):
    name = 'grid/select-nothing'

    def run(self, api):
        api.subs.selected_lines = []


class VideoPlayCurrentLineCommand(BaseCommand):
    name = 'video/play-current-line'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        sel = api.subs.lines[api.subs.selected_lines[0]]
        api.video.play(sel.start, sel.end)


class VideoPlayAroundSelectionCommand(BaseCommand):
    name = 'video/play-around-sel'

    def enabled(self, api):
        return api.audio.has_selection

    def run(self, api, delta_start, delta_end):
        api.video.play(
            api.audio.selection_start + delta_start,
            api.audio.selection_end + delta_end)


class VideoPlayAroundSelectionStartCommand(BaseCommand):
    name = 'video/play-around-sel-start'

    def enabled(self, api):
        return api.audio.has_selection

    def run(self, api, delta_start, delta_end):
        api.video.play(
            api.audio.selection_start + delta_start,
            api.audio.selection_start + delta_end)


class VideoPlayAroundSelectionEndCommand(BaseCommand):
    name = 'video/play-around-sel-end'

    def enabled(self, api):
        return api.audio.has_selection

    def run(self, api, delta_start, delta_end):
        api.video.play(
            api.audio.selection_end + delta_start,
            api.audio.selection_end + delta_end)


class VideoStepFrameCommand(BaseCommand):
    name = 'video/step-frame'

    def enabled(self, api):
        return len(api.video.timecodes) > 0

    def run(self, api, delta):
        current_pts = api.video.current_pts
        idx = bisect.bisect_left(api.video.timecodes, current_pts)
        if idx + delta not in range(len(api.video.timecodes)):
            return
        api.video.seek(api.video.timecodes[idx + delta])


class VideoTogglePauseCommand(BaseCommand):
    name = 'video/toggle-pause'

    def run(self, api):
        if api.video.is_paused:
            api.video.unpause()
        else:
            api.video.pause()


class VideoUnpauseCommand(BaseCommand):
    name = 'video/unpause'

    def run(self, api):
        if not api.video.is_paused:
            return
        api.video.unpause()


class VideoPauseCommand(BaseCommand):
    name = 'video/pause'

    def run(self, api):
        if api.video.is_paused:
            return
        api.video.pause()
