"""Decode inspected THUG Xbox/DX9 little-endian texture dictionaries.

Original and decoded images remain local. The parser preserves every mip and
exports lossless PNG bytes for preview; it does not emulate THUG material passes.
"""
import argparse
import binascii
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import zlib

from import_thug_rig import THUG_PIN

MAX_BYTES = 256 * 1024 * 1024
MAX_TEXTURES = 4096
MAX_DIMENSION = 8192
MAX_PIXELS = 64 * 1024 * 1024


class Reader:
    def __init__(self, data):
        if len(data) > MAX_BYTES:
            raise ValueError("Texture dictionary exceeds the supported size limit")
        self.data, self.offset = data, 0

    def read(self, fmt, label):
        size = struct.calcsize("<" + fmt)
        if size > len(self.data) - self.offset:
            raise ValueError(f"Truncated {label} at byte {self.offset}")
        values = struct.unpack_from("<" + fmt, self.data, self.offset)
        self.offset += size
        return values

    def block(self, size, label):
        return self.read(f"{size}s", label)[0]


def checksum(value):
    return f"0x{value:08x}"


def dimensions(width, height, level):
    return max(1, width >> level), max(1, height >> level)


def expected_size(width, height, depth, dxt):
    if dxt in (1, 2, 5):
        return max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * (8 if dxt in (1, 2) else 16)
    return width * height * (depth // 8)


def unswizzle(data, width, height, byte_depth):
    if len(data) != width * height * byte_depth:
        raise ValueError("Swizzled mip size disagrees with its dimensions and texel depth")
    output = bytearray(len(data))
    for pixel in range(width * height):
        half_width, half_height = width // 2, height // 2
        x = y = 0
        x_bit = y_bit = source_bit = 1
        while half_width or half_height:
            if half_width:
                half_width //= 2
                if pixel & source_bit: x |= x_bit
                x_bit *= 2
                source_bit *= 2
            if half_height:
                half_height //= 2
                if pixel & source_bit: y |= y_bit
                y_bit *= 2
                source_bit *= 2
        if x >= width or y >= height:
            raise ValueError("Unsupported non-power-of-two swizzled texture layout")
        start = pixel * byte_depth
        target = (x + y * width) * byte_depth
        output[target:target + byte_depth] = data[start:start + byte_depth]
    return bytes(output)


def color_565(value):
    r, g, b = (value >> 11) & 31, (value >> 5) & 63, value & 31
    return (r * 255 // 31, g * 255 // 63, b * 255 // 31, 255)


def dxt_colors(block, transparent):
    first, second = struct.unpack_from("<HH", block)
    a, b = color_565(first), color_565(second)
    if first > second or not transparent:
        return (a, b, tuple((2 * a[i] + b[i]) // 3 for i in range(4)), tuple((a[i] + 2 * b[i]) // 3 for i in range(4)))
    return (a, b, tuple((a[i] + b[i]) // 2 for i in range(4)), (0, 0, 0, 0))


def decode_dxt(data, width, height, dxt):
    block_bytes = 8 if dxt in (1, 2) else 16
    columns, rows = max(1, (width + 3) // 4), max(1, (height + 3) // 4)
    if len(data) != columns * rows * block_bytes:
        raise ValueError("DXT mip size disagrees with its block dimensions")
    output = bytearray(width * height * 4)
    for by in range(rows):
        for bx in range(columns):
            block = data[(by * columns + bx) * block_bytes:(by * columns + bx + 1) * block_bytes]
            if dxt == 5:
                alpha0, alpha1 = block[0], block[1]
                if alpha0 > alpha1:
                    alphas = [alpha0, alpha1] + [((8 - i) * alpha0 + (i - 1) * alpha1) // 7 for i in range(2, 8)]
                else:
                    alphas = [alpha0, alpha1] + [((6 - i) * alpha0 + (i - 1) * alpha1) // 5 for i in range(2, 6)] + [0, 255]
                alpha_bits = int.from_bytes(block[2:8], "little")
                colors = dxt_colors(block[8:], False)
                color_bits = int.from_bytes(block[12:16], "little")
            else:
                alphas, alpha_bits = None, 0
                colors = dxt_colors(block, True)
                color_bits = int.from_bytes(block[4:8], "little")
            for y in range(4):
                for x in range(4):
                    px, py = bx * 4 + x, by * 4 + y
                    if px >= width or py >= height: continue
                    index = y * 4 + x
                    color = list(colors[(color_bits >> (2 * index)) & 3])
                    if alphas is not None: color[3] = alphas[(alpha_bits >> (3 * index)) & 7]
                    target = (py * width + px) * 4
                    output[target:target + 4] = bytes(color)
    return bytes(output)


def decode_mip(data, width, height, depth, dxt, palette):
    if dxt:
        return decode_dxt(data, width, height, dxt)
    linear = unswizzle(data, width, height, depth // 8)
    if depth == 8:
        if palette is None:
            raise ValueError("8-bit texture has no palette")
        entries = [palette[index:index + 4] for index in range(0, len(palette), 4)]
        if any(value >= len(entries) for value in linear):
            raise ValueError("Palette index outside the supplied color table")
        # D3DCOLOR is numeric ARGB; little-endian memory bytes are BGRA.
        return b"".join(bytes((entries[value][2], entries[value][1], entries[value][0], entries[value][3])) for value in linear)
    if depth == 16:
        output = bytearray()
        for value in struct.unpack(f"<{width * height}H", linear):
            output.extend(((value >> 10 & 31) * 255 // 31, (value >> 5 & 31) * 255 // 31,
                           (value & 31) * 255 // 31, 255 if value & 0x8000 else 0))
        return bytes(output)
    if depth == 32:
        output = bytearray()
        for index in range(0, len(linear), 4):
            b, g, r, a = linear[index:index + 4]
            output.extend((r, g, b, a))
        return bytes(output)
    raise ValueError("Unsupported direct-color texture depth")


def png(rgba, width, height):
    if len(rgba) != width * height * 4:
        raise ValueError("RGBA buffer size disagrees with image dimensions")
    def make(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xffffffff)
    raw = b"".join(b"\0" + rgba[row * width * 4:(row + 1) * width * 4] for row in range(height))
    return b"\x89PNG\r\n\x1a\n" + make(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) + make(b"IDAT", zlib.compress(raw, 9)) + make(b"IEND", b"")


def parse(data):
    reader = Reader(data)
    version, count = reader.read("ii", "texture dictionary header")
    if not 0 <= count <= MAX_TEXTURES:
        raise ValueError("Texture count exceeds the supported dictionary bounds")
    textures, seen = [], set()
    total_pixels = 0
    for index in range(count):
        start = reader.offset
        identity, width, height, levels, depth, palette_depth, dxt, palette_size = reader.read("8I", "texture header")
        if identity in seen:
            raise ValueError("Duplicate texture checksum")
        seen.add(identity)
        if not 1 <= width <= MAX_DIMENSION or not 1 <= height <= MAX_DIMENSION or width & (width - 1) or height & (height - 1):
            raise ValueError("Texture dimensions must be power-of-two and within the inspected loader bounds")
        maximum_levels = int(math.log2(max(width, height))) + 1
        if not 1 <= levels <= maximum_levels:
            raise ValueError("Texture mip count exceeds its dimensions")
        if dxt not in (0, 1, 2, 5) or (dxt == 0 and depth not in (8, 16, 32)):
            raise ValueError("Unsupported THUG texture encoding")
        if dxt and (depth != (4 if dxt in (1, 2) else 8) or palette_size):
            raise ValueError("Compressed texture metadata is inconsistent")
        if depth == 8 and dxt == 0:
            if palette_depth != 32 or palette_size not in (32 * 4, 256 * 4):
                raise ValueError("Paletted texture requires a 32- or 256-entry D3DCOLOR palette")
        elif palette_size:
            raise ValueError("Palette data is only valid for 8-bit textures")
        elif palette_depth:
            raise ValueError("Palette depth is only valid for 8-bit textures")
        palette = reader.block(palette_size, "texture palette") if palette_size else None
        mips = []
        for level in range(levels):
            mip_width, mip_height = dimensions(width, height, level)
            size = reader.read("I", "mip size")[0]
            expected = expected_size(mip_width, mip_height, depth, dxt)
            if size != expected:
                raise ValueError("Mip byte count disagrees with texture format and dimensions")
            raw = reader.block(size, "mip data")
            rgba = decode_mip(raw, mip_width, mip_height, depth, dxt, palette)
            mips.append({"level": level, "width": mip_width, "height": mip_height,
                         "source_size": size, "source_sha256": hashlib.sha256(raw).hexdigest(),
                         "rgba_sha256": hashlib.sha256(rgba).hexdigest(), "rgba": rgba})
            total_pixels += mip_width * mip_height
            if total_pixels > MAX_PIXELS:
                raise ValueError("Decoded texture pixel limit exceeded")
        textures.append({"index": index, "source_id": checksum(identity), "source_offset": start,
                         "source_end": reader.offset, "width": width, "height": height, "levels": levels,
                         "texel_depth": depth, "palette_depth": palette_depth, "dxt": dxt,
                         "palette_entries": palette_size // 4, "palette_sha256": hashlib.sha256(palette).hexdigest() if palette else None,
                         "format": {0: f"argb{depth}-swizzled", 1: "dxt1", 2: "dxt1-code-2", 5: "dxt5"}[dxt], "mips": mips})
    if reader.offset != len(data):
        raise ValueError("Unexpected data after texture dictionary")
    return {"schema_version": 1, "kind": "gonkskate-thug-texture-dictionary", "source_game": "thug",
            "source_format": "tex-xbox-little-endian", "source_version": version, "version_verified": False,
            "source_sha256": hashlib.sha256(data).hexdigest(), "inspected_upstream_commit": THUG_PIN,
            "texture_count": count, "total_decoded_pixels": total_pixels, "source_end": reader.offset,
            "retail_validated": False, "textures": textures}


def metadata(dictionary):
    return {key: value for key, value in dictionary.items() if key != "textures"} | {"textures": [
        {key: value for key, value in texture.items() if key != "mips"} | {"mips": [
            {key: value for key, value in mip.items() if key != "rgba"} for mip in texture["mips"]]}
        for texture in dictionary["textures"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dictionary", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New local output directory")
    args = parser.parse_args()
    try:
        if args.dictionary.stat().st_size > MAX_BYTES:
            raise ValueError("Texture dictionary exceeds the supported size limit")
        parsed = parse(args.dictionary.read_bytes())
        images = [(texture["source_id"][2:] + ".png", png(texture["mips"][0]["rgba"], texture["width"], texture["height"]))
                  for texture in parsed["textures"]]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.mkdir()
        try:
            for name, image in images:
                (args.output / name).write_bytes(image)
            (args.output / "textures.json").write_text(json.dumps(metadata(parsed), indent=2) + "\n", encoding="utf-8")
        except BaseException:
            shutil.rmtree(args.output)
            raise
    except (OSError, ValueError) as error:
        parser.exit(1, f"Texture import failed: {error}\n")
    print(f"Imported {parsed['texture_count']} local textures: {args.output}")


if __name__ == "__main__":
    main()
