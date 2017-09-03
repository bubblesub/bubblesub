#!/usr/bin/env python3
import argparse
import bubblesub.opt
import bubblesub.ui


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?')
    parser.add_argument('--no-config', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()

    opt = bubblesub.opt.Options(
        None if args.no_config else bubblesub.opt.DEFAULT_PATH)

    print('loading API...')
    from bubblesub.api import Api

    print('loading commands...')
    from bubblesub import cmd as _

    api = Api(opt)

    print('loading UI...')
    ui = bubblesub.ui.Ui(api, args)

    ui.run()

    if not args.no_config:
        opt.save(opt.location)


if __name__ == '__main__':
    main()
