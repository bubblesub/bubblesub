#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import bubblesub.ui


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    return parser.parse_args()


def get_config_location():
    return Path('~/.config/bubblesub').expanduser()


def main():
    args = parse_args()

    config_location = get_config_location()
    config_location.mkdir(parents=True, exist_ok=True)
    ui = bubblesub.ui.Ui(config_location, args)
    ui.run()


if __name__ == '__main__':
    main()
