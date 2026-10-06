"""Synthetic THUG character streams and meaningful malformed/GLB checks."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

from import_thug_character import build, import_files
from import_thug_rig import parse as parse_rig
from import_thug_skin import decode_weights, parse as parse_skin, triangles
from test_thug_rig import fixture as rig_fixture


def material_fixture(identity=100, effects=False, passes=1):
    data = struct.pack("<4IBfBBiB", identity, identity + 1, passes, 127, 1, 0.25, 0, 1, 3, int(effects))
    if effects:
        data += struct.pack("<fi", 12, 3)
    data += struct.pack("<f", 8 if effects else 0)
    if effects:
        data += struct.pack("<3f", 0.2, 0.4, 0.6)
    for index in range(passes):
        flags = (1 | 2 | (1 << 11)) if effects else 4
        data += struct.pack("<IIB3fQII2fI", 0x1234 + index, flags, 1, 0.5, 0.5, 0.5,
                            (128 << 32) | 5, 0, 1, 2, 3, 4)
        if flags & 1:
            data += struct.pack("<8f", *range(8))
        if index == 0 and flags & 2:
            data += struct.pack("<IIii4Bi4B", 1, 2, -3, 10, 1, 2, 3, 4, 20, 5, 6, 7, 8)
        if flags & (1 << 11):
            data += struct.pack("<4i4I", 2, 100, 0, -2, 0, 0x1234, 100, 0x2345)
        data += struct.pack("<4I", 1, 2, 0xc1000000, 4)
    return data


def sector_fixture(identity=200, flags=0x817, weighted=True, indices=None, joints=None, packed=None):
    if not weighted:
        flags &= ~0x10
    positions = [(0, 0, 0), (12, 0, 0), (0, 12, 0), (12, 12, 0), (24, 12, 0), (24, 0, 0)]
    if indices is None:
        indices = [[0, 1, 2, 2, 3, 3, 4, 5], [0, 1, 2]]
    count = len(positions)
    data = struct.pack("<IiII10fii", identity, -1, flags, 1, 0, 0, 0, 24, 12, 0,
                       12, 6, 0, 14, count, 40)
    data += b"".join(struct.pack("<3f", *v) for v in positions)
    if flags & 4:
        data += struct.pack("<" + "3f" * count, *([0, 0, 1] * count))
    if flags & 0x10:
        if packed is None:
            packed = [1023, 512 | (511 << 11), 256 | (256 << 11) | (255 << 22)] * 2
        data += struct.pack(f"<{count}I", *packed)
        if joints is None:
            joints = [0, 1, 2, 65535] * count
        data += struct.pack(f"<{4 * count}H", *joints)
    if flags & 1:
        data += struct.pack("<i", 2)
        data += struct.pack("<" + "4f" * count, *([0.25, 0.75, -0.5, 2] * count))
    if flags & 2:
        data += struct.pack(f"<{count}I", *([0xff102030] * count))
    if flags & 0x800:
        data += struct.pack(f"<{count}b", *([0, -1, 1, 0, -1, 1]))
    data += struct.pack("<10fIII", 12, 6, 0, 14, 0, 0, 0, 24, 12, 0,
                        0x800 if flags & 0x800 else 0, 100, len(indices))
    for strip in indices:
        data += struct.pack("<i", len(strip)) + struct.pack(f"<{len(strip)}H", *strip)
    return data


def skin_fixture(effects=False, passes=1, sectors=None):
    sectors = sectors or [sector_fixture()]
    return (struct.pack("<4I", 7, 8, 9, 1) + material_fixture(effects=effects, passes=passes) +
            struct.pack("<i", len(sectors)) + b"".join(sectors) + struct.pack("<i", 0))


def boundary_rig_fixture():
    names = tuple(10 + 10 * i for i in range(63))
    parents = (0,) + names[:-1]
    # Include a rotated root and long parent chain, not just identity matrices.
    half = 2 ** -0.5
    poses = [(0, 0, half, half, 0, 0, 0, 0)] + [(0, 0, 0, 1, 0, 1, 0, 0)] * 62
    return rig_fixture(names=names, parents=parents, flips=(0,) * 63, poses=poses)


def unpack_glb(data):
    magic, version, length = struct.unpack_from("<III", data)
    assert (magic, version, length) == (0x46546c67, 2, len(data))
    size, kind = struct.unpack_from("<II", data, 12)
    assert kind == 0x4e4f534a
    document = json.loads(data[20:20 + size])
    offset = 20 + size
    binary_size, binary_kind = struct.unpack_from("<II", data, offset)
    assert binary_kind == 0x004e4942 and binary_size % 4 == 0
    binary = data[offset + 8:]
    assert len(binary) == binary_size
    assert document["buffers"][0]["byteLength"] <= len(binary)
    return document, binary


def accessor_rows(document, binary, index):
    accessor = document["accessors"][index]
    view = document["bufferViews"][accessor["bufferView"]]
    components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[accessor["type"]]
    fmt = "<" + {5126: "f", 5123: "H"}[accessor["componentType"]] * components
    size = struct.calcsize(fmt)
    assert view["byteOffset"] % 4 == 0
    assert view["byteLength"] == size * accessor["count"]
    assert view["byteOffset"] + view["byteLength"] <= document["buffers"][0]["byteLength"]
    return [struct.unpack_from(fmt, binary, view["byteOffset"] + i * size) for i in range(accessor["count"])]


class CharacterTests(unittest.TestCase):
    def test_original_streams_and_optional_material_branches(self):
        mesh = parse_skin(skin_fixture(effects=True, passes=4), "xbox")
        sector = mesh["sectors"][0]
        self.assertEqual(mesh["source_version_words"], [7, 8, 9])
        self.assertFalse(mesh["version_words_verified"])
        self.assertEqual(sector["positions_inches"][1], [12, 0, 0])
        self.assertEqual(sector["joints"][0], [0, 1, 2, 65535])
        self.assertEqual(sector["uvs"][0], [0.25, 0.75, -0.5, 2])
        self.assertEqual(sector["colors_argb"][0], 0xff102030)
        self.assertEqual(sector["vertex_color_wibble_indices"][1], -1)
        material = mesh["materials"][0]
        self.assertEqual(material["passes"][0]["texture_animation"]["keys"][1], [100, 0x2345])
        self.assertEqual(material["passes"][0]["vertex_color_wibble"][0]["keys"][0], [10, 1, 2, 3, 4])

    def test_explicit_weight_semantics(self):
        self.assertEqual(decode_weights(1023, "xbox"), [1, 0, 0, 0])
        self.assertEqual(decode_weights(1023, "dx9"), [1023 / 1024, 0, 0, 0])
        for value in (0, 0x400, 0x400 << 11, 0x200 << 22, 1023 | (1023 << 11)):
            with self.assertRaises(ValueError):
                decode_weights(value, "xbox")
        with self.assertRaises(ValueError):
            parse_skin(skin_fixture(), "auto")

    def test_original_dummy_material_dictionary_resolution(self):
        tail = struct.pack("<i", 1) + sector_fixture() + struct.pack("<i", 0)
        data = (struct.pack("<4I", 7, 8, 9, 3) + material_fixture(0) +
                material_fixture(0, effects=True) + material_fixture(100) + tail)
        mesh = parse_skin(data, "dx9")
        self.assertEqual([m["dictionary_effective"] for m in mesh["materials"]], [True, False, True])
        glb, _ = build(parse_rig(rig_fixture()), mesh)
        self.assertEqual(len(unpack_glb(glb)[0]["materials"]), 2)
        data = struct.pack("<4I", 7, 8, 9, 2) + material_fixture(100) * 2 + tail
        with self.assertRaises(ValueError):
            parse_skin(data, "dx9")

    def test_strip_parity_survives_degenerate_connectors(self):
        self.assertEqual(triangles([0, 1, 2, 2, 3, 3, 4, 5]), [0, 1, 2, 4, 3, 5])

    def test_glb_rig_bindings_units_weights_and_colors(self):
        rig = parse_rig(rig_fixture())
        raw = skin_fixture()
        mesh = parse_skin(raw, "dx9")
        data, summary = build(rig, mesh)
        document, binary = unpack_glb(data)
        for index in range(len(document["accessors"])):
            accessor_rows(document, binary, index)
        primitive = document["meshes"][0]["primitives"][0]
        attrs = primitive["attributes"]
        self.assertAlmostEqual(accessor_rows(document, binary, attrs["POSITION"])[1][0], 12 * 0.0254)
        self.assertEqual(accessor_rows(document, binary, attrs["JOINTS_0"])[0], (0, 0, 0, 0))
        for row in accessor_rows(document, binary, attrs["WEIGHTS_0"]):
            self.assertAlmostEqual(sum(row), 1, places=6)
        rgba = accessor_rows(document, binary, attrs["COLOR_0"])[0]
        for a, b in zip(rgba, [16 / 255, 32 / 255, 48 / 255, 1]):
            self.assertAlmostEqual(a, b)
        self.assertEqual(document["skins"][0]["joints"], [1, 2, 3])
        self.assertEqual(document["nodes"][2]["children"], [3])
        self.assertEqual(accessor_rows(document, binary, primitive["indices"]), [(0,), (1,), (2,), (4,), (3,), (5,)])
        # Rest-world * inverse-bind is identity. Decode the actual GLB IBM,
        # not just its JSON provenance, and verify neutral skinning.
        inverse = accessor_rows(document, binary, document["skins"][0]["inverseBindMatrices"])
        for bone, column_matrix in zip(rig["bones"], inverse):
            world = bone["rest_world_matrix"]
            matrix = [column_matrix[c * 4 + r] for r in range(4) for c in range(4)]
            for r in range(4):
                for c in range(4):
                    actual = sum(world[r * 4 + k] * matrix[k * 4 + c] for k in range(4))
                    self.assertAlmostEqual(actual, int(r == c), places=6)
        self.assertEqual(summary["triangle_count"], 2)
        self.assertFalse(summary["playable_character_registered"])
        self.assertEqual(mesh, parse_skin(raw, "dx9"), "Preview must not modify raw imported data")

    def test_truncation_bounds_and_unknown_layout_rejected(self):
        data = skin_fixture(effects=True, passes=4)
        for size in range(len(data)):
            with self.assertRaises(ValueError, msg=f"truncation at {size}"):
                parse_skin(data[:size], "xbox")
        with self.assertRaises(ValueError):
            parse_skin(data + b"extra", "xbox")
        for fmt, offset, value in [("I", 12, 999999), ("I", 24, 5), ("I", 28, 256), ("B", 32, 2)]:
            damaged = bytearray(data)
            struct.pack_into("<" + fmt, damaged, offset, value)
            with self.assertRaises(ValueError):
                parse_skin(damaged, "xbox")
        for sector in [sector_fixture(indices=[[0, 1, 99]]), sector_fixture(indices=[[0, 1, 2], [3, 4, 5]]),
                       sector_fixture(flags=0x13), sector_fixture(flags=0x00800017)]:
            with self.assertRaises(ValueError):
                parse_skin(skin_fixture(sectors=[sector]), "xbox")

    def test_missing_bones_and_rigid_attachments_rejected(self):
        rig = parse_rig(rig_fixture())
        for sector in [sector_fixture(joints=[9, 1, 2, 0] * 6), sector_fixture(weighted=False)]:
            with self.assertRaises(ValueError):
                build(rig, parse_skin(skin_fixture(sectors=[sector]), "xbox"))
        mesh = parse_skin(skin_fixture(), "xbox")
        mesh["sectors"][0]["bone_index"] = 1
        with self.assertRaises(ValueError):
            build(rig, mesh)

    def test_rotated_rig_and_maximum_bone_indices(self):
        rig = parse_rig(boundary_rig_fixture())
        mesh = parse_skin(skin_fixture(sectors=[sector_fixture(joints=[0, 31, 62, 65535] * 6)]), "xbox")
        data, _ = build(rig, mesh)
        document, binary = unpack_glb(data)
        skin = document["skins"][0]
        self.assertEqual(len(skin["joints"]), 63)
        self.assertEqual(len(accessor_rows(document, binary, skin["inverseBindMatrices"])), 63)
        attrs = document["meshes"][0]["primitives"][0]["attributes"]
        self.assertIn(62, accessor_rows(document, binary, attrs["JOINTS_0"])[2])
        self.assertEqual(document["nodes"][1]["children"], [2])
        self.assertEqual(document["nodes"][63]["name"], "bone_00000276")

    def test_output_preservation_and_failed_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            ske, skin, out = folder / "local.ske", folder / "local.skin", folder / "character"
            ske.write_bytes(rig_fixture())
            skin.write_bytes(skin_fixture())
            package = import_files(ske, skin, out, "xbox")
            before = (out / "character.glb").read_bytes()
            self.assertTrue(package["summary"]["bone_count"] == 3)
            with self.assertRaises(FileExistsError):
                import_files(ske, skin, out, "xbox")
            self.assertEqual((out / "character.glb").read_bytes(), before)
            skin.write_bytes(b"bad")
            with self.assertRaises(ValueError):
                import_files(ske, skin, folder / "failed", "xbox")
            self.assertFalse((folder / "failed").exists())


if __name__ == "__main__":
    unittest.main()
