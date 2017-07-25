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
