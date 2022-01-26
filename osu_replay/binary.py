import struct


class BinaryReader:
    def __init__(self, data_view: memoryview) -> None:
        self.data_view = data_view

    def read_raw_view(self, length: int) -> memoryview:
        val = self.data_view[:length]
        self.data_view = self.data_view[length:]
        return val

    def read_i8(self) -> int:
        val = self.data_view[0]
        self.data_view = self.data_view[1:]
        return val - 256 if val > 127 else val

    def read_u8(self) -> int:
        val = self.data_view[0]
        self.data_view = self.data_view[1:]
        return val

    def read_i16(self) -> int:
        (val,) = struct.unpack("<h", self.data_view[:2])
        self.data_view = self.data_view[2:]
        return val

    def read_u16(self) -> int:
        (val,) = struct.unpack("<H", self.data_view[:2])
        self.data_view = self.data_view[2:]
        return val

    def read_i32(self) -> int:
        (val,) = struct.unpack("<i", self.data_view[:4])
        self.data_view = self.data_view[4:]
        return val

    def read_u32(self) -> int:
        (val,) = struct.unpack("<I", self.data_view[:4])
        self.data_view = self.data_view[4:]
        return val

    def read_i64(self) -> int:
        (val,) = struct.unpack("<q", self.data_view[:8])
        self.data_view = self.data_view[8:]
        return val

    def read_u64(self) -> int:
        (val,) = struct.unpack("<Q", self.data_view[:8])
        self.data_view = self.data_view[8:]
        return val

    # floating-point types

    def read_f16(self) -> float:
        (val,) = struct.unpack_from("<e", self.data_view[:2])
        self.data_view = self.data_view[2:]
        return val

    def read_f32(self) -> float:
        (val,) = struct.unpack_from("<f", self.data_view[:4])
        self.data_view = self.data_view[4:]
        return val

    def read_f64(self) -> float:
        (val,) = struct.unpack_from("<d", self.data_view[:8])
        self.data_view = self.data_view[8:]
        return val

    def read_uleb128(self) -> int:
        val = shift = 0

        while True:
            b = self.read_u8()  # TODO: measure if worth inlining?

            val |= (b & 127) << shift
            if (b & 128) == 0:
                break

            shift += 7

        return val

    def read_string(self) -> str:
        if self.read_u8() == 0:  # TODO: measure if worth inlining?
            return ""

        string_length = self.read_uleb128()
        val = self.data_view[:string_length].tobytes().decode()
        self.data_view = self.data_view[string_length:]
        return val


# write functions
def write_uleb128(num: int) -> bytes:
    if num == 0:
        return b"\x00"

    val = bytearray()
    length = 0

    while num > 0:
        val.append(num & 127)
        num >>= 7
        if num != 0:
            val[length] |= 128
        length += 1

    return val


def write_string(string: str) -> bytes:
    if string:
        bytestring = string.encode()
        val = b"\x0b" + write_uleb128(len(bytestring)) + bytestring
    else:
        val = b"\x00"

    return val
