# Default commands
| Command name | Description |
|:-------------|:------------|
|`file/new` | Opens a new file.<br>Prompts user to save the current file if there are unsaved changes. |
|`file/open` | Opens an existing subtitles file.<br>Prompts user to save the current file if there are unsaved changes. Prompts user to choose where to load the file from if the path wasn't specified in the command arguments.<br>Parameters:<br><ol><li>path (path, optional): optional path to load the subtitles from</li></ol> |
|`file/load‑video` | Loads a video file for the audio/video playback.<br>Prompts user to choose where to load the file from if the path wasn't specified in the command arguments.<br>Parameters:<br><ol><li>path (path, optional): optional path to load the video from</li></ol> |
|`file/save` | Saves the current subtitles to an ASS file.<br>If the currently loaded subtitles weren't ever saved, prompts user to choose where to save the file to. |
|`file/save‑as` | Saves the current subtitles to an ASS file.<br>Prompts user to choose where to save the file to if the path wasn't specified in the command arguments.<br>Parameters:<br><ol><li>path (path, optional): optional path to save the subtitles to</li></ol> |
|`file/quit` | Quits the application.<br>Prompts user to save the current file if there are unsaved changes. |
|`grid/jump‑to‑line` | Jumps to the specified line.<br>Prompts user for the line number with a GUI dialog. |
|`grid/jump‑to‑time` | Jumps to the specified time.<br>Prompts user for details with a GUI dialog. |
|`grid/select‑prev‑sub` | Selects the subtitle above the first currently selected subtitle. |
|`grid/select‑next‑sub` | Selects the subtitle below the last currently selected subtitle. |
|`grid/select‑all` | Selects all subtitles. |
|`grid/select‑nothing` | Clears subtitle selection. |
|`grid/copy‑text‑to‑clipboard` | Copies text from the subtitle selection. |
|`grid/copy‑times‑to‑clipboard` | Copies time boundaries from the subtitle selection. |
|`grid/paste‑times‑from‑clipboard` | Pastes time boundaries into the subtitle selection. |
|`grid/copy‑to‑clipboard` | Copies the selected subtitles. |
|`grid/paste‑from‑clipboard‑below` | Pastes subtitles below the selection. |
|`grid/paste‑from‑clipboard‑above` | Pastes subtitles above the selection. |
|`grid/create‑audio‑sample` | Saves current subtitle selection to a WAV file.<br>The audio starts at the first selected subtitle start and ends at the last selected subtitle end. |
|`edit/undo` | Undoes last edit operation. |
|`edit/redo` | Redoes last edit operation. |
|`edit/insert‑above` | Inserts one empty subtitle above the current subtitle selection. |
|`edit/insert‑below` | Inserts one empty subtitle below the current subtitle selection. |
|`edit/move‑up` | Moves the selected subtitles up. |
|`edit/move‑down` | Moves the selected subtitles down. |
|`edit/move‑to` | Moves the selected subtitles to the specified position.<br>Asks for the position interactively. |
|`edit/duplicate` | Duplicates the selected subtitles.<br>The newly created subtitles are interleaved with the current selection. |
|`edit/delete` | Deletes the selected subtitles. |
|`edit/swap‑text‑and‑notes` | Swaps subtitle text with their notes in the selected subtitles. |
|`edit/split‑sub‑at‑video` | Splits the selected subtitle into two at the current video frame. |
|`edit/join‑subs/keep‑first` | Joins the selected subtitles together.<br>Keeps only the first subtitle's properties. |
|`edit/join‑subs/concatenate` | Joins the selected subtitles together.<br>Keeps the first subtitle's properties and concatenates the text and notes of the consecutive subtitles. |
|`edit/shift‑subs‑with‑gui` | Shifts the subtitle boundaries by the specified distance.<br>Prompts user for details with a GUI dialog. |
|`edit/snap‑subs‑start‑to‑video` | Snaps selected subtitles' start to the current video frame. |
|`edit/snap‑subs‑end‑to‑video` | Snaps selected subtitles' end to the current video frame. |
|`edit/place‑subs‑at‑video` | Realigns the selected subtitles to the current video frame.<br>The subtitles start time is placed at the current video frame and the subtitles duration is set to the default subtitle duration. |
|`edit/snap‑subs‑start‑to‑prev‑sub` | Snaps the selected subtitles start times to the subtitle above. |
|`edit/snap‑subs‑end‑to‑next‑sub` | Snaps the selected subtitles end times to the subtitle below. |
|`edit/shift‑subs‑start` | Shifts selected subtitles start times by the specified distance.<br>Parameters:<br><ol><li>delta (integer): milliseconds to shift the subtitles by</li></ol> |
|`edit/shift‑subs‑end` | Shifts selected subtitles end times by the specified distance.<br>Parameters:<br><ol><li>delta (integer): milliseconds to shift the subtitles by</li></ol> |
|`edit/shift‑subs` | Shifts selected subtitles by the specified distance.<br>Parameters:<br><ol><li>delta (integer): milliseconds to shift the subtitles by</li></ol> |
|`edit/search` | Opens up the search dialog. |
|`edit/search‑and‑replace` | Opens up the search and replace dialog. |
|`edit/search‑repeat` | Repeats last search operation.<br>Parameters:<br><ol><li>direction (integer): 1 to search forward, -1 to search backward</li></ol> |
|`audio/scroll` | Scrolls the waveform viewport horizontally by its width's percentage.<br>Parameters:<br><ol><li>delta (real number): factor to shift the view by</li></ol> |
|`audio/zoom` | Zooms the waveform viewport in or out by the specified factor.<br>Parameters:<br><ol><li>delta (integer): factor to zoom the view by</li></ol> |
|`audio/snap‑sel‑start‑to‑video` | Snaps the waveform selection start to nearest video frame. |
|`audio/snap‑sel‑end‑to‑video` | Snaps the waveform selection end to nearest video frame. |
|`audio/place‑sel‑at‑video` | Realigns the selection to the current video frame.<br>The selection start is placed at the current video frame and the selection size is set to the default subtitle duration. |
|`audio/snap‑sel‑start‑to‑prev‑sub` | Snaps the waveform selection start to the subtitle above. |
|`audio/snap‑sel‑end‑to‑next‑sub` | Snaps the waveform selection end to the subtitle below. |
|`audio/shift‑sel‑start` | Shifts the waveform selection start by the specified distance.<br>Parameters:<br><ol><li>delta (integer): amount to shift the selection by</li><li>frames (boolean): if true, shift by frames; otherwise by milliseconds</li></ol> |
|`audio/shift‑sel‑end` | Shifts the waveform selection end by the specified distance.<br>Parameters:<br><ol><li>delta (integer): amount to shift the selection</li><li>frames (boolean): if true, shift by frames; otherwise by milliseconds</li></ol> |
|`audio/shift‑sel` | Shifts the waveform selection start/end by the specified distance.<br>Parameters:<br><ol><li>delta (integer): amount to shift the selection</li><li>frames (boolean): if true, shift by frames; otherwise by milliseconds</li></ol> |
|`audio/commit‑sel` | Commits the waveform selection into the current subtitle.<br>The selected subtitle start and end times is synced to the current waveform selection boundaries. |
|`video/play‑current‑line` | Plays the currently selected subtitle. |
|`video/play‑around‑sel` | Plays a region near the current waveform selection.<br>Parameters:<br><ol><li>delta_start (integer): delta relative to the selection start inmilliseconds</li><li>delta_end (integer): delta relative to the selection end in milliseconds</li></ol> |
|`video/play‑around‑sel‑start` | Plays a region near the current waveform selection start.<br>Parameters:<br><ol><li>delta_start (integer): delta relative to the selection start inmilliseconds</li><li>delta_end (integer): delta relative to the selection start in milliseconds</li></ol> |
|`video/play‑around‑sel‑end` | Plays a region near the current waveform selection end.<br>Parameters:<br><ol><li>delta_start (integer): delta relative to the selection end in milliseconds</li><li>delta_end (integer): delta relative to the selection end in milliseconds</li></ol> |
|`video/step‑frame` | Seeks the video by the specified amount of frames.<br>Parameters:<br><ol><li>delta (integer): how many frames to step</li></ol> |
|`video/step‑ms` | Seeks the video by the specified milliseconds.<br>Parameters:<br><ol><li>delta (integer): how many milliseconds to step</li><li>precise (boolean): whether to use precise seekingat the expense of performance</li></ol> |
|`video/seek‑with‑gui` | Seeks the video to the desired place.<br>Prompts user for details with a GUI dialog. |
|`video/set‑playback‑speed` | Adjusts the video playback speed.<br>Parameters:<br><ol><li>expr (string): expression to calculate new playback speed</li></ol> |
|`video/toggle‑pause` | Pauses or unpauses the video playback. |
|`video/unpause` | Unpauses the video playback. |
|`video/pause` | Pauses the video playback. |
|`video/screenshot` | Makes a screenshot of the current video frame.<br>Prompts user for the path where to save the screenshot to.<br>Parameters:<br><ol><li>include_subtitles (boolean): whether to "burn" the subtitles intothe screenshot</li></ol> |
|`video/set‑volume` | Adjusts the video volume.<br>Parameters:<br><ol><li>expr (string): expression to calculate new volume</li></ol> |
|`edit/karaoke‑split` | Splits the selected subtitles according to the karaoke tags inside. |
|`edit/karaoke‑join` | Joins the selected subtitles adding karaoke timing tags inbetween. |
|`edit/transformation‑join` | Joins the selected subtitles adding animation timing tags inbetween.<br>The syllables appear one after another. |
|`view/set‑palette` | Changes the GUI color theme.<br>Parameters:<br><ol><li>palette_name (string): name of the palette to change to</li></ol> |
|`view/focus‑text‑editor` | Focuses the subtitle text edit field. |
|`view/focus‑note‑editor` | Focuses the subtitle note edit field. |
|`view/focus‑grid` | Focuses the subtitles grid. |
|`view/focus‑spectrogram` | Focuses the audio waveform. |
|`edit/spell‑check` | Opens up the spell check dialog. |
|`edit/manage‑styles` | Opens up the style manager. |
|`misc/reload‑plugins` | Reloads the user plugins. |
