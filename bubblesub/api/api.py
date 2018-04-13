import argparse

import bubblesub.api.cmd
import bubblesub.api.gui
import bubblesub.api.log
import bubblesub.api.media
import bubblesub.api.subs
import bubblesub.api.undo
import bubblesub.opt


class Api:
    def __init__(
            self,
            opt: bubblesub.opt.Options,
            args: argparse.Namespace
    ) -> None:
        self.opt = opt
        self.log = bubblesub.api.log.LogApi()
        self.gui = bubblesub.api.gui.GuiApi(self)
        self.subs = bubblesub.api.subs.SubtitlesApi()
        self.media = bubblesub.api.media.MediaApi(
            self.subs, self.log, opt, args
        )
        self.undo = bubblesub.api.undo.UndoApi(self.subs)
        self.cmd = bubblesub.api.cmd.CommandApi(self)
