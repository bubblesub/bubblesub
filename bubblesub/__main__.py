#!/usr/bin/env python3
import argparse
from pathlib import Path
import bubblesub.opt
import bubblesub.ui


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?')
    parser.add_argument('--no-config', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()

    cfg_path = Path('~/.config/bubblesub').expanduser()

    opt = bubblesub.opt.Options()
    if not args.no_config:
        opt.load(cfg_path)

    print('Loading API...')
    from bubblesub.api import Api

    print('Loading commands...')
    from bubblesub import cmd as _

    api = Api(opt)
    api.cmd.load_plugins(cfg_path / 'scripts')

    print('Loading UI...')
    bubblesub.ui.Ui(api, args).run()
    if not args.no_config:
        opt.save(cfg_path)


if __name__ == '__main__':
    main()
