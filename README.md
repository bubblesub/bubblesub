<p align='center'>
    <img src='bubblesub/ui/assets/bubblesub-textured.png' alt='logo' width='50%'/>
</p>

<p align='center'>
    Simple extensible ASS subtitle editor for Linux
    <br />
    <br />
    <a href="https://github.com/bubblesub/bubblesub/actions">
        <img src="https://github.com/bubblesub/bubblesub/workflows/bubblesub/badge.svg">
    </a>
</p>


## Features

- **Python - easily extend it however you want**
- Video preview
- Audio preview (spectrogram)
- Video band for quick assessment of scene boundaries
- Audio and video are synced at all times
- Spectrogram shows where subs start and end
- Slow playback support (with audio pitch correction)
- **I can sub an entire episode without ever having to touch the mouse**
- Mouse users are not excluded and can click their way to all the commands
- **Robust plugin API** (everything GUI is capable of can be done through the API)
- **Simple architecture** (Commands ↔ API ↔ GUI)
- Separate control for persistent inline comments (useful for translating)
- Newlines support in the editor
- Everything is aligned to video frames
- Style editor with realistic preview
- Vim mode in the text editor (off by default, requires neovim 0.4+)
- No bloat

## Screenshot

![](docs/screen.png)

## Installation

- Install system dependencies
    - Python 3.6
    - [`libmpv`](https://github.com/mpv-player/mpv.git)
    - [`ffms`](https://github.com/FFMS/ffms2)
    - [`fftw`](https://github.com/FFTW/fftw3)
    - `Qt5` bindings
- Clone the repository: `git clone https://github.com/bubblesub/bubblesub`
- Enter its directory: `cd bubblesub`
- Install `bubblesub`: `pip install --user .`
- Run bubblesub: `python3 -m bubblesub` or simply `bubblesub`

If you want to simplify `bubblesub` installation, look at our [Dockerfile](Dockerfile).
You will find what dependencies are needed, how to install them and how to run 
our tests.

## Documentation

#### Default hotkeys and commands

Please see [this file](docs/doc.md).

#### API

For the API documentation, for now please consult the docstrings in the
`bubblesub.api` module. In the future, if bubblesub experiences a boost in
popularity, this might be improved.

#### Configuration and plugins

- `$XDG_CONFIG_HOME/bubblesub/`: contains user configuration
    - `options.yaml`: general options
    - `hotkeys.conf`: configurable user hotkeys
    - `menu.conf`: configurable additional user menus
- `$XDG_CONFIG_HOME/bubblesub/scripts`: contains user plugins (see [example
plugin](docs/example_plugin.py))
- `$XDG_CACHE_HOME/bubblesub/`: used to cache time codes and such

## Questions

1. I want to report a bug.

    Please use GitHub issues.

2. I want a feature.

    Chances are I'm too busy to work on features I don't personally need,
    so pull requests are strongly encouraged.

3. Why not aegisub?

    Because it doesn't cover my needs, it's too convoluted and its development
    is too slow.

4. Windows builds?

    You can find a Windows build for bubblesub [here](https://github.com/Luni-4/bubblesub/tree/windows).  
    I don't maintain it, so please contact the current developer if you find some issue.

5. Versioning? PyPI?

    I don't say no, maybe in the future, if the project gets more popular.
    For now, `git master` is the way to go.

## Contact

**Issue tracker**: [GitHub issues](https://github.com/bubblesub/bubblesub)

## Acknowledgments

I'd like to thank all
[contributors](https://github.com/bubblesub/bubblesub/graphs/contributors) for the
help on this project.  
The lovely logo was donated by fri. Thanks :)
