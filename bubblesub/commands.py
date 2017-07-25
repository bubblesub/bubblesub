import bubblesub.ui.util


DEFAULT_SUB_DURATION = 2000  # TODO: move this to config
commands_dict = {}


# i *really* hate this idiom
def command(command_name):
    def fish(function):
        def blub(*args, **kwargs):
            function(*args, **kwargs)
        commands_dict[command_name] = blub
        return blub
    return fish


def _ask_about_unsaved_changes(api):
    # TODO: ask only when necessary
    return bubblesub.ui.util.ask(
        'Are you sure you want to close the current file?')


@command('file/save')
def cmd_save(api):
    api.save_ass(api.ass_path)
    # TODO: log in console


@command('file/quit')
def cmd_quit(api):
    api.gui.quit()


@command('edit/insert-above')
def cmd_edit_insert_above(api):
    if not api.selected_lines:
        idx = 0
        prev_sub = None
        cur_sub = None
    else:
        idx = api.selected_lines[0]
        prev_sub = api.subtitles.get(idx - 1)
        cur_sub = api.subtitles[idx]

    end = cur_sub.start if cur_sub else DEFAULT_SUB_DURATION
    start = end - DEFAULT_SUB_DURATION
    if start < 0:
        start = 0
    if prev_sub and start < prev_sub.end:
        start = prev_sub.end
    if start > end:
        start = end
    api.subtitles.insert_one(idx, start=start, end=end, style='Default')
    api.selected_lines = [idx]


@command('edit/insert-below')
def cmd_edit_insert_below(api):
    if not api.selected_lines:
        idx = 0
        cur_sub = None
        next_sub = api.subtitles.get(0)
    else:
        idx = api.selected_lines[-1]
        cur_sub = api.subtitles[idx]
        idx += 1
        next_sub = api.subtitles.get(idx)

    start = cur_sub.end if cur_sub else 0
    end = start + DEFAULT_SUB_DURATION
    if next_sub and end > next_sub.start:
        end = next_sub.start
    if end < start:
        end = start
    api.subtitles.insert_one(idx, start=start, end=end, style='Default')
    api.selected_lines = [idx]


@command('edit/duplicate')
def cmd_edit_duplicate(api):
    if not api.selected_lines:
        return
    new_selection = []
    api.gui.begin_update()
    for idx in reversed(sorted(api.selected_lines)):
        sub = api.subtitles[idx]
        api.subtitles.insert_one(
            idx + 1,
            start=sub.start,
            end=sub.end,
            actor=sub.actor,
            style=sub.style,
            text=sub.text)
        new_selection.append(idx + len(api.selected_lines) - len(new_selection))
    api.selected_lines = new_selection
    api.gui.end_update()


@command('edit/delete')
def cmd_edit_delete(api):
    if not api.selected_lines:
        return
    for idx in reversed(sorted(api.selected_lines)):
        api.subtitles.remove(idx, 1)
    api.selected_lines = []


@command('edit/glue-sel-start')
def cmd_glue_sel_start(api):
    if api.audio.has_selection \
            and api.selected_lines and api.selected_lines[0] > 0:
        api.audio.select(
            api.subtitles[api.selected_lines[0] - 1].end,
            api.audio.selection_end)


@command('edit/glue-sel-end')
def cmd_glue_sel_start(api):
    if api.audio.has_selection and \
            api.selected_lines and \
            api.selected_lines[-1] + 1 < len(api.subtitles):
        api.audio.select(
            api.audio.selection_start,
            api.subtitles[api.selected_lines[-1] + 1].start)


@command('edit/move-sel-start')
def cmd_move_sel_start(api, ms):
    if api.audio.has_selection:
        api.audio.select(
            min(api.audio.selection_end, api.audio.selection_start + ms),
            api.audio.selection_end)


@command('edit/move-sel-end')
def cmd_move_sel_end(api, ms):
    if api.audio.has_selection:
        api.audio.select(
            api.audio.selection_start,
            max(api.audio.selection_start, api.audio.selection_end + ms))


@command('edit/commit-sel')
def cmd_edit_commit_selection(api):
    for idx in api.selected_lines:
        subtitle = api.subtitles[idx]
        subtitle.begin_update()
        subtitle.start = api.audio.selection_start
        subtitle.end = api.audio.selection_end
        subtitle.end_update()


@command('grid/select-prev-subtitle')
def cmd_grid_select_prev_sub(api):
    if not api.selected_lines:
        if not api.subtitles:
            return
        api.selected_lines = [len(api.subtitles) - 1, 0]
    else:
        api.selected_lines = [max(0, api.selected_lines[0] - 1)]


@command('grid/select-next-subtitle')
def cmd_grid_select_next_sub(api):
    if not api.selected_lines:
        if not api.subtitles:
            return
        api.selected_lines = [0]
    else:
        api.selected_lines = [
            min(api.selected_lines[0] + 1, len(api.subtitles) - 1)]


@command('grid/select-all')
def cmd_grid_select_all(api):
    api.selected_lines = list(range(len(api.subtitles)))


@command('grid/select-nothing')
def cmd_grid_select_nothing(api):
    api.selected_lines = []


@command('video/play-current-line')
def cmd_video_play_current_line(api):
    if api.selected_lines:
        sel = api.subtitles[api.selected_lines[0]]
        api.video.play(sel.start, sel.end)


@command('video/play-around-sel')
def cmd_video_play_around_sel_start(api, delta_start, delta_end):
    if api.audio.has_selection:
        api.video.play(
            api.audio.selection_start + delta_start,
            api.audio.selection_end + delta_end)


@command('video/play-around-sel-start')
def cmd_video_play_around_sel_start(api, delta_start, delta_end):
    if api.audio.has_selection:
        api.video.play(
            api.audio.selection_start + delta_start,
            api.audio.selection_start + delta_end)


@command('video/play-around-sel-end')
def cmd_video_play_around_sel_end(api, delta_start, delta_end):
    if api.audio.has_selection:
        api.video.play(
            api.audio.selection_end + delta_start,
            api.audio.selection_end + delta_end)


@command('video/toggle-pause')
def cmd_video_toggle_pause(api):
    if api.video.is_paused:
        api.video.unpause()
    else:
        api.video.pause()


@command('video/unpause')
def cmd_video_unpause(api):
    if not api.video.is_paused:
        return
    api.video.unpause()


@command('video/pause')
def cmd_video_pause(api):
    if api.video.is_paused:
        return
    api.video.pause()
