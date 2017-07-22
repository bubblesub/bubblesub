import bubblesub.ui.util


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


@command('select/prev-subtitle')
def cmd_select_prev_sub(api):
    if not api.selected_lines:
        if not api.subtitles:
            return
        api.selected_lines = [len(api.subtitles) - 1, 0]
    else:
        api.selected_lines = [max(0, api.selected_lines[0] - 1)]


@command('select/next-subtitle')
def cmd_select_next_sub(api):
    if not api.selected_lines:
        if not api.subtitles:
            return
        api.selected_lines = [0]
    else:
        api.selected_lines = [
            min(api.selected_lines[0] + 1, len(api.subtitles) - 1)]


@command('select/all')
def cmd_select_all(api):
    api.selected_lines = list(range(len(api.subtitles)))


@command('select/nothing')
def cmd_select_nothing(api):
    api.selected_lines = []


@command('play/unpause')
def cmd_unpause(api):
    if not api.video.is_paused:
        return
    api.video.unpause()


@command('play/pause')
def cmd_pause(api):
    if api.video.is_paused:
        return
    api.video.pause()
