"""Synthetic THUG texture dictionaries, all supported decoders and GLB use."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from import_thug_character import import_files
from import_thug_texture import decode_dxt, parse, png, unswizzle
from test_thug_character import rig_fixture, sector_fixture, skin_fixture, unpack_glb


def swizzle(linear, width, height, depth):
    # Invert the exact inspected Unswizzle mapping for fixture creation.
    output = bytearray(len(linear))
    for source in range(width * height):
        half_width, half_height = width // 2, height // 2
        x = y = 0
        x_bit = y_bit = bit = 1
        while half_width or half_height:
            if half_width:
                half_width //= 2
                if source & bit: x |= x_bit
                x_bit *= 2; bit *= 2
            if half_height:
                half_height //= 2
                if source & bit: y |= y_bit
                y_bit *= 2; bit *= 2
        output[source * depth:(source + 1) * depth] = linear[(x + y * width) * depth:(x + y * width + 1) * depth]
    return bytes(output)


def bc1_block(first=0xf800, second=0x07e0, indices=0xe4e4e4e4):
    return struct.pack("<HHI", first, second, indices)


def bc3_block(alpha0=255, alpha1=0, alpha_bits=0x053977053977, first=0x001f, second=0xffff, indices=0x1b1b1b1b):
    return struct.pack("<BB", alpha0, alpha1) + alpha_bits.to_bytes(6, "little") + struct.pack("<HHI", first, second, indices)


def texture_record(identity, width, height, depth, dxt, levels, palette=b"", mips=None):
    mips = mips or []
    data = struct.pack("<8I", identity, width, height, levels, depth, 32 if palette else 0, dxt, len(palette)) + palette
    return data + b"".join(struct.pack("<I", len(mip)) + mip for mip in mips)


def texture_fixture(records=None, version=3):
    if records is None:
        rgba = bytes((0x30, 0x20, 0x10, 0xff)) * 16  # source BGRA -> red=0x10
        records = [texture_record(0x1234, 4, 4, 32, 0, 1, mips=[swizzle(rgba, 4, 4, 4)])]
    return struct.pack("<ii", version, len(records)) + b"".join(records)


def png_rgba(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    offset, chunks = 8, {}
    while offset < len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        chunks.setdefault(kind, bytearray()).extend(data[offset + 8:offset + 8 + size])
        offset += 12 + size
    width, height = struct.unpack_from(">II", chunks[b"IHDR"])
    raw = zlib.decompress(chunks[b"IDAT"])
    return width, height, b"".join(raw[row * (1 + width * 4) + 1:(row + 1) * (1 + width * 4)] for row in range(height))


class TextureTests(unittest.TestCase):
    def test_direct_swizzled_formats_and_mips(self):
        rgba32 = bytes((3, 2, 1, 4)) * 16
        values16 = [0xfc00, 0x83e0, 0x801f, 0xffff] * 4
        raw16 = struct.pack("<16H", *values16)
        palette = b"".join(bytes((index, 0, 255 - index, 128 + index % 128)) for index in range(256))
        indices = bytes(range(16))
        records = [texture_record(1, 4, 4, 32, 0, 2, mips=[swizzle(rgba32, 4, 4, 4), swizzle(rgba32[:16], 2, 2, 4)]),
                   texture_record(2, 4, 4, 16, 0, 1, mips=[swizzle(raw16, 4, 4, 2)]),
                   texture_record(3, 4, 4, 8, 0, 1, palette, [swizzle(indices, 4, 4, 1)])]
        result = parse(texture_fixture(records))
        self.assertEqual(result["texture_count"], 3)
        self.assertEqual(result["source_end"], len(texture_fixture(records)))
        self.assertEqual(result["textures"][0]["mips"][0]["rgba"][:4], bytes((1, 2, 3, 4)))
        self.assertEqual(result["textures"][1]["mips"][0]["rgba"][:4], bytes((255, 0, 0, 255)))
        self.assertEqual(result["textures"][2]["mips"][0]["rgba"][:4], bytes((255, 0, 0, 128)))
        self.assertEqual(unswizzle(swizzle(rgba32, 4, 4, 4), 4, 4, 4), rgba32)

    def test_dxt1_code2_dxt5_and_edge_blocks(self):
        records = [texture_record(10 + index, 4, 4, 4, code, 1, mips=[bc1_block()]) for index, code in enumerate((1, 2))]
        records += [texture_record(12, 8, 2, 8, 5, 1, mips=[bc3_block() * 2])]
        result = parse(texture_fixture(records))
        self.assertEqual(result["textures"][0]["mips"][0]["rgba"], decode_dxt(bc1_block(), 4, 4, 1))
        self.assertEqual(result["textures"][0]["mips"][0]["rgba"], result["textures"][1]["mips"][0]["rgba"])
        self.assertEqual(len(result["textures"][2]["mips"][0]["rgba"]), 8 * 2 * 4)
        transparent = decode_dxt(bc1_block(0, 0xffff, 0xffffffff), 4, 4, 1)
        self.assertEqual(transparent[3::4], bytes(16))

    def test_png_is_lossless_rgba(self):
        rgba = bytes(range(64))
        encoded = png(rgba, 4, 4)
        self.assertEqual(png_rgba(encoded), (4, 4, rgba))

    def test_every_truncation_boundary_and_invalid_metadata(self):
        valid = texture_fixture()
        for length in range(len(valid)):
            with self.subTest(length=length), self.assertRaises(ValueError): parse(valid[:length])
        with self.assertRaises(ValueError): parse(valid + b"tail")
        cases = [(4, "i", 4097), (12, "I", 3), (16, "I", 3), (20, "I", 4), (24, "I", 7),
                 (28, "I", 7), (32, "I", 99), (36, "I", 4), (40, "I", 1)]
        for offset, fmt, value in cases:
            damaged = bytearray(valid)
            struct.pack_into("<" + fmt, damaged, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError): parse(damaged)
        duplicate = texture_fixture([texture_record(1, 4, 4, 4, 1, 1, mips=[bc1_block()])] * 2)
        with self.assertRaises(ValueError): parse(duplicate)

    def test_textured_character_glb_embeds_png_and_preserves_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ske, skin, textures = [root / name for name in ("c.ske", "c.skin", "c.tex")]
            ske.write_bytes(rig_fixture()); skin.write_bytes(skin_fixture()); textures.write_bytes(texture_fixture())
            package = import_files(ske, skin, root / "out", "dx9", textures=textures)
            document, binary = unpack_glb((root / "out/character.glb").read_bytes())
            self.assertTrue(package["summary"]["textures_imported"])
            self.assertEqual(package["summary"]["texture_count"], 1)
            self.assertNotIn('"rgba":', json.dumps(package))
            material = document["materials"][0]
            self.assertEqual(material["pbrMetallicRoughness"]["baseColorTexture"], {"index": 0, "texCoord": 0})
            image = document["images"][0]
            view = document["bufferViews"][image["bufferView"]]
            embedded = binary[view["byteOffset"]:view["byteOffset"] + view["byteLength"]]
            self.assertEqual(png_rgba(embedded), (4, 4, bytes((0x10, 0x20, 0x30, 0xff)) * 16))
            self.assertEqual(textures.read_bytes(), texture_fixture())
            missing = texture_fixture([texture_record(99, 4, 4, 4, 1, 1, mips=[bc1_block()])])
            textures.write_bytes(missing)
            with self.assertRaises(ValueError): import_files(ske, skin, root / "bad", "dx9", textures=textures)
            self.assertFalse((root / "bad").exists())
            textures.write_bytes(texture_fixture())
            skin.write_bytes(skin_fixture(sectors=[sector_fixture(flags=0x816)]))
            with self.assertRaisesRegex(ValueError, "no source UV"):
                import_files(ske, skin, root / "no-uv", "dx9", textures=textures)
            self.assertFalse((root / "no-uv").exists())


if __name__ == "__main__":
    unittest.main()
