import sys
import time
import traceback
import io
import bubblesub.ui.main_window
import bubblesub.ui.util
from PyQt5 import QtWidgets


def excepthook(exception_type, exception_value, traceback_object):
    separator = '-' * 80

    with io.StringIO() as handle:
        traceback.print_tb(traceback_object, None, handle)
        handle.seek(0)
        traceback_info = handle.read()

    msg = '\n'.join([
        'An unhandled exception occurred.',
        time.strftime("%Y-%m-%d, %H:%M:%S"),
        separator,
        '%s: \n%s' % (str(exception_type), str(exception_value)),
        separator,
        traceback_info
    ])

    print(msg)
    bubblesub.ui.util.error(msg)


sys.excepthook = excepthook


class Ui:
    def __init__(self, opt, api, args):
        self._opt = opt
        self._api = api
        self._args = args

    def run(self):
        app = QtWidgets.QApplication(sys.argv)
        main_window = bubblesub.ui.main_window.MainWindow(self._opt, self._api)
        self._api.gui.main_window = main_window

        if self._args.file:
            self._api.subs.load_ass(self._args.file)

        main_window.show()
        app.exec_()
