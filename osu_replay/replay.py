#!/usr/bin/env python3
import lzma
import struct
from typing import Optional

from osu_replay import binary

# References
# 1. https://osu.ppy.sh/wiki/en/Client/File_formats/Osr_%28file_format%29


class ReplayFrame:
    __slots__ = (
        "delta",
        "x",
        "y",
        "keys",
    )

    def __init__(
        self,
        delta: int,
        x: float,
        y: float,
        keys: int,
    ) -> None:
        self.delta = delta
        self.x = x
        self.y = y
        self.keys = keys


class Replay:
    __slots__ = (
        "mode",
        "osu_version",
        "map_md5",
        "player_name",
        "replay_md5",
        "n300",
        "n100",
        "n50",
        "ngeki",
        "nkatu",
        "nmiss",
        "score",
        "max_combo",
        "perfect",
        "mods",
        "life_graph",
        "timestamp",
        "frames",
        "score_id",
        "mod_extras",
        "seed",
        "skip_offset",
    )

    def __init__(
        self,
        mode: int,
        osu_version: int,
        map_md5: str,
        player_name: str,
        replay_md5: str,
        n300: int,
        n100: int,
        n50: int,
        ngeki: int,
        nkatu: int,
        nmiss: int,
        score: int,
        max_combo: int,
        perfect: int,
        mods: int,
    ) -> None:
        self.mode = mode
        self.osu_version = osu_version
        self.map_md5 = map_md5
        self.player_name = player_name
        self.replay_md5 = replay_md5
        self.n300 = n300
        self.n100 = n100
        self.n50 = n50
        self.ngeki = ngeki
        self.nkatu = nkatu
        self.nmiss = nmiss
        self.score = score
        self.max_combo = max_combo
        self.perfect = perfect
        self.mods = mods

        # TODO: ugly :(

        self.life_graph: list[tuple[int, float]] = []
        self.timestamp = 0

        self.frames: list[ReplayFrame] = []

        self.score_id: int = 0
        self.mod_extras: Optional[float] = None
        self.seed = 0
        self.skip_offset = 0

    @classmethod
    def from_data_view(cls, data_view: memoryview) -> "Replay":
        reader = binary.BinaryReader(data_view)

        replay = cls(
            ## read replay headers
            mode=reader.read_u8(),
            osu_version=reader.read_i32(),
            map_md5=reader.read_string(),
            player_name=reader.read_string(),
            replay_md5=reader.read_string(),
            n300=reader.read_u16(),
            n100=reader.read_u16(),
            n50=reader.read_u16(),
            ngeki=reader.read_u16(),
            nkatu=reader.read_u16(),
            nmiss=reader.read_u16(),
            score=reader.read_i32(),
            max_combo=reader.read_u16(),
            perfect=reader.read_u8(),
            mods=reader.read_i32(),
        )

        ## read replay life graph
        replay.life_graph = []

        life_bar_string = reader.read_string()
        for entry in life_bar_string.split(",")[:-1]:
            split = entry.split("|", maxsplit=1)
            replay.life_graph.append((int(split[0]), float(split[1])))

        replay.timestamp = reader.read_i64()

        ## read replay frames
        replay.frames = []

        # read compressed data
        compressed_data_length = reader.read_i32()
        compressed_data = reader.read_raw_view(compressed_data_length)

        # decompress data, parse into actions
        decompressed_data = lzma.decompress(compressed_data, format=lzma.FORMAT_ALONE)

        actions = [x for x in decompressed_data.split(b",") if x]

        # the first two actions are special
        # the second contains the skip offset, if any
        skip_offset = actions[1].split(b"|", maxsplit=1)[0]
        if skip_offset != b"-1":
            replay.skip_offset = int(skip_offset)

            if replay.mods & (1 << 11):  # autoplay
                replay.skip_offset -= 100000

        for action in actions[2:-1]:
            split = action.split(b"|", maxsplit=3)

            replay.frames.append(
                ReplayFrame(
                    delta=int(split[0]),
                    x=float(split[1]),
                    y=float(split[2]),
                    keys=int(split[3]),
                )
            )

        # the last action is special
        # it contains the seed for mania's random mod
        if replay.osu_version >= 2013_03_19:
            replay.seed = int(actions[-1].rsplit(b"|", maxsplit=1)[1])

        # read replay trailers
        if replay.osu_version >= 2014_07_21:
            replay.score_id = reader.read_i64()
        elif replay.osu_version >= 2012_10_08:
            replay.score_id = reader.read_i32()

        if replay.mods & (1 << 23):  # target practice
            replay.mod_extras = reader.read_f64()

        return replay

    @classmethod
    def from_data(cls, data: bytes) -> "Replay":
        with memoryview(data) as data_view:
            return cls.from_data_view(data_view)

    @classmethod
    def from_file(cls, filename: str) -> "Replay":
        with open(filename, "rb") as f:
            with memoryview(f.read()) as data_view:
                return cls.from_data_view(data_view)

    def to_file(self, filename: str) -> None:
        data = bytearray()

        # write replay headers
        data += struct.pack("<Bi", self.mode, self.osu_version)
        data += binary.write_string(self.map_md5)
        data += binary.write_string(self.player_name)
        data += binary.write_string(self.replay_md5)
        data += struct.pack(
            "<HHHHHHiH?i",
            self.n300,
            self.n100,
            self.n50,
            self.ngeki,
            self.nkatu,
            self.nmiss,
            self.score,
            self.max_combo,
            self.perfect,
            self.mods,
        )

        # write replay life graph
        data += binary.write_string(
            ",".join(
                [
                    # TODO: not this
                    f"{x[0]}|{x[1] if x[1] % 1 != 0 else int(x[1])}"
                    for x in self.life_graph
                ]
            )
            + ","
        )

        data += struct.pack("<q", self.timestamp)

        # write replay body
        decompressed_data = bytearray()
        decompressed_data += b"0|256|-500|0,"
        decompressed_data += f"-1|256|-500|{self.skip_offset},".encode()
        decompressed_data += (
            b",".join(
                [  # TODO: not this
                    f"{frame.delta}|{frame.x if frame.x %  1 != 0 else int(frame.x)}|{frame.y if frame.y % 1 != 0 else int(frame.y)}|{frame.keys}".encode()
                    for frame in self.frames
                ]
            )
            + b","
        )
        if self.osu_version >= 2013_03_19:
            decompressed_data += f"-12345|0|0|{self.seed},".encode()

        compressed_data = lzma.compress(decompressed_data, format=lzma.FORMAT_ALONE)

        data += struct.pack("<i", len(compressed_data))
        data += compressed_data

        # write replay trailers
        if self.osu_version >= 2014_07_21:
            data += struct.pack("<q", self.score_id)
        elif self.osu_version >= 2012_10_08:
            data += struct.pack("<i", self.score_id)

        if self.mods & (1 << 23):  # target practice
            data += struct.pack("<d", self.mod_extras)

        # write data to output file
        with open(filename, "wb+") as f:
            f.write(data)


def test_this_bad_boy_out() -> int:
    """Test out replay reading & writing."""

    print("Parsing `replay.osr`")
    replay = Replay.from_file("replay.osr")

    print("Adding relax to the replay")
    replay.mods |= 1 << 7

    print("Writing the replay to `replay_relax.osr`")
    replay.to_file("replay_relax.osr")

    return 0


if __name__ == "__main__":
    raise SystemExit(test_this_bad_boy_out())
