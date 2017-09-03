import asyncio
import sys
import bubblesub.ui.main_window
import bubblesub.ui.util
import quamash
from PyQt5 import QtWidgets


def run(api, args):
    app = QtWidgets.QApplication(sys.argv)
    loop = quamash.QEventLoop(app)
    asyncio.set_event_loop(loop)

    if not args.no_config:
        api.opt.load(api.opt.DEFAULT_PATH)

    main_window = bubblesub.ui.main_window.MainWindow(api)
    api.gui.set_main_window(main_window)

    if args.file:
        api.subs.load_ass(args.file)

    if not args.no_config:
        try:
            api.cmd.load_plugins(api.opt.location / 'scripts')
        except Exception as ex:
            api.log.error(str(ex))

    main_window.show()
    with loop:
        loop.run_forever()

    if not args.no_config:
        api.opt.save(api.opt.location)
