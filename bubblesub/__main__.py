#!/usr/bin/env python3
import argparse
import bubblesub.opt
import bubblesub.ui


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?')
    parser.add_argument('--no-config', action='store_true')
    parser.add_argument('--no-video', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()

    opt = bubblesub.opt.Options()

    print('loading API...')
    from bubblesub.api import Api

    print('loading commands...')
    from bubblesub import cmd as _

    api = Api(opt, args)

    print('loading UI...')
    bubblesub.ui.run(api, args)


if __name__ == '__main__':
    main()
