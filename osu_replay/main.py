#!/usr/bin/env python3
"""A command-line interface for working with osu! replays."""

import argparse
import sys
from typing import Optional, Sequence

from osu_replay import Replay


def _print_metadata(filename: str, replay: Replay) -> None:
    print("metadata for:", filename)
    print("  mode:", replay.mode)
    print("  osu! version:", replay.osu_version)
    print("  map md5:", replay.map_md5)
    print("  player name:", replay.player_name)
    print("  replay md5:", replay.replay_md5)
    print("  300s:", replay.n300)
    print("  100s:", replay.n100)
    print("  50s:", replay.n50)
    print("  gekis:", replay.ngeki)
    print("  katus:", replay.nkatu)
    print("  misses:", replay.nmiss)
    print("  score:", replay.score)
    print("  max combo:", replay.max_combo)
    print("  perfect:", replay.perfect)
    print("  mods:", replay.mods)
    # print("  Life graph:", replay.life_graph)
    print("  timestamp:", replay.timestamp)
    # print("  Frames:", replay.frames)
    print("  score id:", replay.score_id)
    print("  mod extras:", replay.mod_extras)
    print("  seed:", replay.seed)
    print("  skip offset:", replay.skip_offset)

    # TODO: print life graph


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog="osu_replay")

    subparsers = parser.add_subparsers(dest="command")

    # $ osu-replay metadata [files ...]
    metadata_parser = subparsers.add_parser("metadata", help="Show replay metadata.")
    metadata_parser.add_argument(
        "files",
        help="The replay files to process.",
        nargs=argparse.ONE_OR_MORE,
    )

    # TODO: `$ osu-replay edit` for editing metadata

    if not argv:
        argv = ["--help"]

    args = parser.parse_args(argv)

    if args.command == "metadata":
        for filename in args.files:
            replay = Replay.from_file(filename)
            _print_metadata(filename, replay)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
