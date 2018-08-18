# Default hotkeys

Context refers to the currently focused widget.

| Shortcut | Context | Command |
|:--|:--|:--|
|<kbd>Ctrl+Shift+N</kbd> | global | <code><a href="#user-content-cmd-new">new</a> </code> |
|<kbd>Ctrl+O</kbd> | global | <code><a href="#user-content-cmd-open">open</a> </code> |
|<kbd>Ctrl+S</kbd> | global | <code><a href="#user-content-cmd-save">save</a> </code> |
|<kbd>Ctrl+Shift+S</kbd> | global | <code><a href="#user-content-cmd-save-as">save-as</a> </code> |
|<kbd>Ctrl+Q</kbd> | global | <code><a href="#user-content-cmd-quit">quit</a> </code> |
|<kbd>Ctrl+G</kbd> | global | <code><a href="#user-content-cmd-select-subs">select-subs</a> ask-number</code> |
|<kbd>Ctrl+Shift+G</kbd> | global | <code><a href="#user-content-cmd-select-subs">select-subs</a> ask-time</code> |
|<kbd>Alt+G</kbd> | global | <code><a href="#user-content-cmd-seek">seek</a> -d=ask</code> |
|<kbd>Ctrl+K</kbd> | global | <code><a href="#user-content-cmd-select-subs">select-subs</a> one-above</code> |
|<kbd>Ctrl+J</kbd> | global | <code><a href="#user-content-cmd-select-subs">select-subs</a> one-below</code> |
|<kbd>Ctrl+A</kbd> | global | <code><a href="#user-content-cmd-select-subs">select-subs</a> all</code> |
|<kbd>Ctrl+Shift+A</kbd> | global | <code><a href="#user-content-cmd-select-subs">select-subs</a> none</code> |
|<kbd>Alt+2</kbd> | global | <code><a href="#user-content-cmd-video-play-around-sel">video/play-around-sel</a> -t start -de 500</code> |
|<kbd>Alt+1</kbd> | global | <code><a href="#user-content-cmd-video-play-around-sel">video/play-around-sel</a> -t start -ds -500</code> |
|<kbd>Alt+3</kbd> | global | <code><a href="#user-content-cmd-video-play-around-sel">video/play-around-sel</a> -t end -ds -500</code> |
|<kbd>Alt+4</kbd> | global | <code><a href="#user-content-cmd-video-play-around-sel">video/play-around-sel</a> -t end -de 500</code> |
|<kbd>Ctrl+R</kbd> | global | <code><a href="#user-content-cmd-video-play-around-sel">video/play-around-sel</a> </code> |
|<kbd>Ctrl+,</kbd> | global | <code><a href="#user-content-cmd-seek">seek</a> -d=-1f</code> |
|<kbd>Ctrl+.</kbd> | global | <code><a href="#user-content-cmd-seek">seek</a> -d=+1f</code> |
|<kbd>Ctrl+Shift+,</kbd> | global | <code><a href="#user-content-cmd-seek">seek</a> -d=-500ms</code> |
|<kbd>Ctrl+Shift+.</kbd> | global | <code><a href="#user-content-cmd-seek">seek</a> -d=+500ms</code> |
|<kbd>Ctrl+T</kbd> | global | <code><a href="#user-content-cmd-video-play-current-sub">video/play-current-sub</a> </code> |
|<kbd>Ctrl+P</kbd> | global | <code><a href="#user-content-cmd-pause">pause</a> toggle</code> |
|<kbd>Ctrl+Z</kbd> | global | <code><a href="#user-content-cmd-undo">undo</a> </code> |
|<kbd>Ctrl+Y</kbd> | global | <code><a href="#user-content-cmd-redo">redo</a> </code> |
|<kbd>Ctrl+F</kbd> | global | <code><a href="#user-content-cmd-search">search</a> </code> |
|<kbd>Ctrl+H</kbd> | global | <code><a href="#user-content-cmd-search-and-replace">search-and-replace</a> </code> |
|<kbd>Ctrl+Return</kbd> | global | <code><a href="#user-content-cmd-edit-insert-sub">edit/insert-sub</a> -d below</code> |
|<kbd>Ctrl+Delete</kbd> | global | <code><a href="#user-content-cmd-delete-subs">delete-subs</a> </code> |
|<kbd>Ctrl+Shift+1</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d=-10f</code> |
|<kbd>Ctrl+Shift+2</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d=+10f</code> |
|<kbd>Ctrl+Shift+3</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d=-10f</code> |
|<kbd>Ctrl+Shift+4</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d=+10f</code> |
|<kbd>Ctrl+1</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d=-1f</code> |
|<kbd>Ctrl+2</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d=+1f</code> |
|<kbd>Ctrl+3</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d=-1f</code> |
|<kbd>Ctrl+4</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d=+1f</code> |
|<kbd>Ctrl+B</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d current-frame</code> |
|<kbd>Ctrl+M</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d current-frame</code> |
|<kbd>Ctrl+N</kbd> | global | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --both -d current-frame</code><br><code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d default-sub-duration</code> |
|<kbd>Ctrl+[</kbd> | global | <code><a href="#user-content-cmd-set-playback-speed">set-playback-speed</a> '{}/1.5'</code> |
|<kbd>Ctrl+]</kbd> | global | <code><a href="#user-content-cmd-set-playback-speed">set-playback-speed</a> '{}*1.5'</code> |
|<kbd>F3</kbd> | global | <code><a href="#user-content-cmd-search-repeat">search-repeat</a> -d below</code> |
|<kbd>Shift+F3</kbd> | global | <code><a href="#user-content-cmd-search-repeat">search-repeat</a> -d above</code> |
|<kbd>Alt+A</kbd> | global | <code><a href="#user-content-cmd-focus-widget">focus-widget</a> spectrogram</code> |
|<kbd>Alt+S</kbd> | global | <code><a href="#user-content-cmd-focus-widget">focus-widget</a> subtitles-grid</code> |
|<kbd>Alt+D</kbd> | global | <code><a href="#user-content-cmd-focus-widget">focus-widget</a> text-editor -s</code> |
|<kbd>Alt+Shift+D</kbd> | global | <code><a href="#user-content-cmd-focus-widget">focus-widget</a> note-editor -s</code> |
|<kbd>Alt+C</kbd> | global | <code><a href="#user-content-cmd-focus-widget">focus-widget</a> console-input -s</code> |
|<kbd>Alt+Shift+C</kbd> | global | <code><a href="#user-content-cmd-focus-widget">focus-widget</a> console</code> |
|<kbd>Alt+X</kbd> | global | <code><a href="#user-content-cmd-edit-split-sub-at-current-video-frame">edit/split-sub-at-current-video-frame</a> </code> |
|<kbd>Alt+J</kbd> | global | <code><a href="#user-content-cmd-edit-join-subs-concatenate">edit/join-subs-concatenate</a> </code> |
|<kbd>Alt+Up</kbd> | global | <code><a href="#user-content-cmd-edit-move-subs">edit/move-subs</a> -d above</code> |
|<kbd>Alt+Down</kbd> | global | <code><a href="#user-content-cmd-edit-move-subs">edit/move-subs</a> -d below</code> |
|<kbd>Alt+Return</kbd> | global | <code><a href="#user-content-cmd-file-properties">file-properties</a> </code> |
|<kbd>Shift+1</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d=-10f</code> |
|<kbd>Shift+2</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d=+10f</code> |
|<kbd>Shift+3</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d=-10f</code> |
|<kbd>Shift+4</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d=+10f</code> |
|<kbd>1</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d=-1f</code> |
|<kbd>2</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d=+1f</code> |
|<kbd>3</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d=-1f</code> |
|<kbd>4</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d=+1f</code> |
|<kbd>C</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-commit-sel">spectrogram-commit-sel</a> </code> |
|<kbd>K</kbd> | spectrogram | <code><a href="#user-content-cmd-edit-insert-sub">edit/insert-sub</a> -d above</code> |
|<kbd>J</kbd> | spectrogram | <code><a href="#user-content-cmd-edit-insert-sub">edit/insert-sub</a> -d below</code> |
|<kbd>R</kbd> | spectrogram | <code><a href="#user-content-cmd-video-play-around-sel">video/play-around-sel</a> </code> |
|<kbd>T</kbd> | spectrogram | <code><a href="#user-content-cmd-video-play-current-sub">video/play-current-sub</a> </code> |
|<kbd>P</kbd> | spectrogram | <code><a href="#user-content-cmd-pause">pause</a> toggle</code> |
|<kbd>Shift+K</kbd> | spectrogram | <code><a href="#user-content-cmd-select-subs">select-subs</a> one-above</code> |
|<kbd>Shift+J</kbd> | spectrogram | <code><a href="#user-content-cmd-select-subs">select-subs</a> one-below</code> |
|<kbd>A</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-scroll">spectrogram-scroll</a> -d -0.05</code> |
|<kbd>F</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-scroll">spectrogram-scroll</a> -d 0.05</code> |
|<kbd>Ctrl+-</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-zoom">spectrogram-zoom</a> -d 1.1</code> |
|<kbd>Ctrl+=</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-zoom">spectrogram-zoom</a> -d 0.9</code> |
|<kbd>Ctrl++</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-zoom">spectrogram-zoom</a> -d 0.9</code> |
|<kbd>,</kbd> | spectrogram | <code><a href="#user-content-cmd-seek">seek</a> -d=-1f</code> |
|<kbd>.</kbd> | spectrogram | <code><a href="#user-content-cmd-seek">seek</a> -d=+1f</code> |
|<kbd>Ctrl+Shift+,</kbd> | spectrogram | <code><a href="#user-content-cmd-seek">seek</a> -d=-1500ms</code> |
|<kbd>Ctrl+Shift+.</kbd> | spectrogram | <code><a href="#user-content-cmd-seek">seek</a> -d=+1500ms</code> |
|<kbd>Shift+,</kbd> | spectrogram | <code><a href="#user-content-cmd-seek">seek</a> -d=-500ms</code> |
|<kbd>Shift+.</kbd> | spectrogram | <code><a href="#user-content-cmd-seek">seek</a> -d=+500ms</code> |
|<kbd>B</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d current-frame</code> |
|<kbd>M</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d current-frame</code> |
|<kbd>N</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --both -d current-frame</code><br><code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d default-sub-duration</code> |
|<kbd>[</kbd> | spectrogram | <code><a href="#user-content-cmd-set-playback-speed">set-playback-speed</a> '{}/1.5'</code> |
|<kbd>]</kbd> | spectrogram | <code><a href="#user-content-cmd-set-playback-speed">set-playback-speed</a> '{}*1.5'</code> |
|<kbd>Alt+Left</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d prev-sub-end</code> |
|<kbd>Alt+Right</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d next-sub-start</code> |
|<kbd>Alt+Shift+Left</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --start -d=-1kf</code> |
|<kbd>Alt+Shift+Right</kbd> | spectrogram | <code><a href="#user-content-cmd-spectrogram-shift-sel">spectrogram-shift-sel</a> --end -d=+1kf</code> |
|<kbd>Ctrl+C</kbd> | subtitles grid | <code><a href="#user-content-cmd-copy-subs">copy-subs</a> </code> |
|<kbd>Ctrl+V</kbd> | subtitles grid | <code><a href="#user-content-cmd-paste-subs">paste-subs</a> -t selected --after</code> |

# Default commands
### <a name="cmd-copy-subs"></a>`copy‑subs`
Copies given subtitles to clipboard.



Usage:
`copy‑subs -t|--target=… -s|--subject=…`



* `-t`, `--target`: subtitles to select
* `-s`, `--subject`: subject to copy (`text`, `times`, `all`)

### <a name="cmd-delete-subs"></a>`delete‑subs`
Deletes given subtitles.



Usage:
`delete‑subs [target]`



* `target`: subtitles to select

### <a name="cmd-edit-duplicate-subs"></a>`edit/duplicate‑subs`
Duplicates the selected subtitles. The newly created subtitles are interleaved with the current selection.
### <a name="cmd-edit-insert-sub"></a>`edit/insert‑sub`
Inserts one empty subtitle near the current subtitle selection.



Usage:
`edit/insert‑sub -d|--direction=…`



* `-d`, `--direction`: how to insert the subtitle (`above`, `below`)

### <a name="cmd-edit-join-subs-as-karaoke"></a>`edit/join‑subs‑as‑karaoke`
Joins the selected subtitles adding karaoke timing tags inbetween.
### <a name="cmd-edit-join-subs-as-transformation"></a>`edit/join‑subs‑as‑transformation`
Joins the selected subtitles adding animation timing tags inbetween. The syllables appear one after another.
### <a name="cmd-edit-join-subs-concatenate"></a>`edit/join‑subs‑concatenate`
Joins the selected subtitles together. Keeps the first subtitle's properties and concatenates the text and notes of the consecutive subtitles.
### <a name="cmd-edit-join-subs-keep-first"></a>`edit/join‑subs‑keep‑first`
Joins the selected subtitles together. Keeps only the first subtitle's properties.
### <a name="cmd-edit-move-subs"></a>`edit/move‑subs`
Moves the selected subtitles above or below.



Usage:
`edit/move‑subs -d|--direction=…`



* `-d`, `--direction`: how to move the subtitles (`above`, `below`)

### <a name="cmd-edit-move-subs-to"></a>`edit/move‑subs‑to`
Moves the selected subtitles to the specified position. Asks for the position interactively.
### <a name="cmd-edit-place-subs-at-current-video-frame"></a>`edit/place‑subs‑at‑current‑video‑frame`
Realigns the selected subtitles to the current video frame. The subtitles start time is placed at the current video frame and the subtitles duration is set to the default subtitle duration.
### <a name="cmd-edit-shift-subs"></a>`edit/shift‑subs`
Shifts selected subtitles times by the specified distance.



Usage:
`edit/shift‑subs -t|--target=… -d|--delta=…`



* `-t`, `--target`: how to shift the subtitles (`start`, `end`, `both`)
* `-d`, `--delta`: milliseconds to shift the subtitles by

### <a name="cmd-edit-shift-subs-with-gui"></a>`edit/shift‑subs‑with‑gui`
Shifts the subtitle boundaries by the specified distance. Prompts user for details with a GUI dialog.
### <a name="cmd-edit-snap-subs-to-current-video-frame"></a>`edit/snap‑subs‑to‑current‑video‑frame`
Snaps selected subtitles to the current video frame.



Usage:
`edit/snap‑subs‑to‑current‑video‑frame -t|--target=…`



* `-t`, `--target`: how to snap the selection (`start`, `end`, `both`)

### <a name="cmd-edit-snap-subs-to-near-sub"></a>`edit/snap‑subs‑to‑near‑sub`
Snaps the selected subtitles times to the nearest subtitle.



Usage:
`edit/snap‑subs‑to‑near‑sub -t|--target=… -d|--direction=…`



* `-t`, `--target`: how to snap the subtitles (`start`, `end`, `both`)
* `-d`, `--direction`: direction to snap into (`above`, `below`)

### <a name="cmd-edit-split-sub-at-current-video-frame"></a>`edit/split‑sub‑at‑current‑video‑frame`
Splits the selected subtitle into two at the current video frame.
### <a name="cmd-edit-split-sub-by-karaoke"></a>`edit/split‑sub‑by‑karaoke`
Splits the selected subtitles according to the karaoke tags inside.
### <a name="cmd-edit-swap-subs-text-and-notes"></a>`edit/swap‑subs‑text‑and‑notes`
Swaps subtitle text with their notes in the selected subtitles.
### <a name="cmd-file-properties"></a>`file‑properties`
Opens up the metadata editor dialog.
### <a name="cmd-focus-widget"></a>`focus‑widget`
Focuses the target widget.



Usage:
`focus‑widget target [-s|--select]`



* `target`: which widget to focus (`text-editor`, `note-editor`, `style-editor`, `actor-editor`, `layer-editor`, `margin-left-editor`, `margin-right-editor`, `margin-vertical-editor`, `start-time-editor`, `end-time-editor`, `duration-editor`, `comment-checkbox`, `subtitles-grid`, `spectrogram`, `console`, `console-input`)
* `-s`, `--select`: whether to select the text

### <a name="cmd-grid-create-audio-sample"></a>`grid/create‑audio‑sample`
Saves current subtitle selection to a WAV file. The audio starts at the first selected subtitle start and ends at the last selected subtitle end.
### <a name="cmd-load-video"></a>`load‑video`
Loads a video file for the audio/video playback. Prompts user to choose where to load the file from if the path wasn't specified in the command arguments.



Usage:
`load‑video [path]`



* `path`: optional path to load the video from

### <a name="cmd-manage-styles"></a>`manage‑styles`
Aliases: `styles-manager`, `style-manager`

Opens up the style manager.
### <a name="cmd-mute"></a>`mute`
Mutes or unmutes the video audio.



Usage:
`mute operation`



* `operation`: whether to mute the audio

### <a name="cmd-new"></a>`new`
Opens a new file. Prompts user to save the current file if there are unsaved changes.
### <a name="cmd-open"></a>`open`
Opens an existing subtitles file. Prompts user to save the current file if there are unsaved changes. Prompts user to choose where to load the file from if the path wasn't specified in the command arguments.



Usage:
`open [path]`



* `path`: path to load the subtitles from

### <a name="cmd-paste-into-subs"></a>`paste‑into‑subs`
Pastes text or times into the given subtitles.



Usage:
`paste‑into‑subs -t|--target=… -s|--subject=…`



* `-t`, `--target`: subtitles to paste the subject into
* `-s`, `--subject`: subject to copy (`text`, `times`)

### <a name="cmd-paste-subs"></a>`paste‑subs`
Pastes subtitles from clipboard.



Usage:
`paste‑subs -t|--target=… [--before] [--after]`



* `-t`, `--target`: where to paste the subtitles
* `--before`: paste before target
* `--after`: paste after target

### <a name="cmd-pause"></a>`pause`
Pauses or unpauses the video playback.



Usage:
`pause operation`



* `operation`: whether to pause the video

### <a name="cmd-quit"></a>`quit`
Quits the application. Prompts user to save the current file if there are unsaved changes.
### <a name="cmd-redo"></a>`redo`
Redoes last edit operation.
### <a name="cmd-reload-plugins"></a>`reload‑plugins`
Reloads the user plugins.
### <a name="cmd-save"></a>`save`
Saves the current subtitles to an ASS file. If the currently loaded subtitles weren't ever saved, prompts user to choose where to save the file to.
### <a name="cmd-save-as"></a>`save‑as`
Saves the current subtitles to an ASS file. Prompts user to choose where to save the file to if the path wasn't specified in the command arguments.



Usage:
`save‑as [path]`



* `path`: optional path to save the subtitles to

### <a name="cmd-search"></a>`search`
Opens up the search dialog.
### <a name="cmd-search-and-replace"></a>`search‑and‑replace`
Opens up the search and replace dialog.
### <a name="cmd-search-repeat"></a>`search‑repeat`
Aliases: `search-again`

Repeats last search operation.



Usage:
`search‑repeat -d|--direction=…`



* `-d`, `--direction`: whether to search forward or backward (`above`, `below`)

### <a name="cmd-seek"></a>`seek`
Changes the video playback position to desired place.



Usage:
`seek -d|--delta=… [-p|--precise]`



* `-d`, `--delta`: amount to shift the selection
* `-p`, `--precise`: whether to use precise seeking at the expense of performance

### <a name="cmd-select-subs"></a>`select‑subs`
Selects given subtitles.



Usage:
`select‑subs target`



* `target`: subtitles to select

### <a name="cmd-set-palette"></a>`set‑palette`
Changes the GUI color theme.



Usage:
`set‑palette palette_name`



* `palette_name`: name of the palette to change to (`dark`, `light`)

### <a name="cmd-set-playback-speed"></a>`set‑playback‑speed`
Adjusts the video playback speed.



Usage:
`set‑playback‑speed expression`



* `expression`: expression to calculate new playback speed

### <a name="cmd-set-volume"></a>`set‑volume`
Adjusts the video volume.



Usage:
`set‑volume expression`



* `expression`: expression to calculate new volume

### <a name="cmd-spectrogram-commit-sel"></a>`spectrogram‑commit‑sel`
Aliases: `spectrogram-commit-selection`

Commits the spectrogram selection into given subtitles. The subtitles start and end times are synced to the current spectrogram selection boundaries.



Usage:
`spectrogram‑commit‑sel -t|--target=…`



* `-t`, `--target`: subtitles to commit selection into

### <a name="cmd-spectrogram-scroll"></a>`spectrogram‑scroll`
Scrolls the spectrogram horizontally by its width's percentage.



Usage:
`spectrogram‑scroll -d|--delta=…`



* `-d`, `--delta`: factor to shift the view by

### <a name="cmd-spectrogram-shift-sel"></a>`spectrogram‑shift‑sel`
Aliases: `spectrogram-shift-selection`

Shfits the spectrogram selection.



Usage:
`spectrogram‑shift‑sel -d|--delta=… [--no-align] [--start] [--end] [--both]`



* `-d`, `--delta`: amount to shift the selection
* `--no-align`: don't realign selection to video frames
* `--start`: shift selection start
* `--end`: shift selection end
* `--both`: shift whole selection

### <a name="cmd-spectrogram-zoom"></a>`spectrogram‑zoom`
Zooms the spectrogram in or out by the specified factor.



Usage:
`spectrogram‑zoom -d|--delta=…`



* `-d`, `--delta`: factor to zoom the view by

### <a name="cmd-spell-check"></a>`spell‑check`
Opens up the spell check dialog.
### <a name="cmd-undo"></a>`undo`
Undoes last edit operation.
### <a name="cmd-video-play-around-sel"></a>`video/play‑around‑sel`
Plays a region near the current spectrogram selection.



Usage:
`video/play‑around‑sel -t|--target=… -ds|--delta-start=… -de|--delta-end=…`



* `-t`, `--target`: part of selection to play around (`start`, `end`, `both`)
* `-ds`, `--delta-start`: delta relative to the selection start in milliseconds
* `-de`, `--delta-end`: delta relative to the selection end in milliseconds

### <a name="cmd-video-play-current-sub"></a>`video/play‑current‑sub`
Plays the currently selected subtitle.
### <a name="cmd-video-screenshot"></a>`video/screenshot`
Makes a screenshot of the current video frame. Prompts user for the path where to save the screenshot to.



Usage:
`video/screenshot [-i|--include-subs]`



* `-i`, `--include-subs`: whether to "burn" the subtitles into the screenshot
