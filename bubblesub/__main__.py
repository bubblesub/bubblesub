#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import bubblesub.api
import bubblesub.opt
import bubblesub.ui


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--no-config', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()

    cfg_path = Path('~/.config/bubblesub').expanduser()

    api = bubblesub.api.Api()
    opt = bubblesub.opt.Options()
    if not args.no_config:
        opt.load(cfg_path)
    ui = bubblesub.ui.Ui(opt, api, args)
    ui.run()
    if not args.no_config:
        opt.save(cfg_path)


if __name__ == '__main__':
    main()
