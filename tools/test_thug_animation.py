"""Synthetic animation streams, source interpolation edge cases and GLB channels."""
import math
from pathlib import Path
import struct
import tempfile
import unittest

from import_thug_animation import (COMPRESSED_TIME, COMPRESS_TABLE, HIRES_COUNTS, PLATFORM, PREROTATED_ROOT,
                                   fast_slerp, parse, rotation, sample, sample_track)
from import_thug_character import build, import_files
from import_thug_rig import parse as parse_rig
from import_thug_skin import parse as parse_skin
from test_thug_character import accessor_rows, boundary_rig_fixture, rig_fixture, skin_fixture, unpack_glb


def tables_fixture():
    q = [(0, 0, 0, 0)] * 256
    t = [(0, 0, 0, 0)] * 256
    q[200], q[201] = (0, 0, 11585, 0), (8192, -8192, 0, 0)
    t[200], t[201] = (64, -96, 32, 0), (-128, 64, 160, 0)
    return tuple(b"".join(struct.pack("<4h", *row) for row in table) for table in (q, t))


def animation_fixture(count=3, compressed=False, hires=False, duration=1.0, tracks=None):
    # Nontrivial first pose proves animation is absolute, not a rest-pose delta.
    tracks = tracks or [([(0, False, (0, 0, 0)), (30, True, (0, 0, 11585)), (60, False, (0, 0, 0))],
                        [(0, (32 * index, 0, 0)), (60, (32 * index, 32, -64))]) for index in range(count)]
    flags = COMPRESSED_TIME | PREROTATED_ROOT | (COMPRESS_TABLE if compressed else PLATFORM) | (HIRES_COUNTS if hires else 0)
    data = struct.pack("<IIf4I", 7, flags, duration, count, sum(len(q) for q, _ in tracks), sum(len(t) for _, t in tracks), 0)
    q_tracks, t_tracks = [], []
    for q, t in tracks:
        q_tracks.append(b"".join(struct.pack("<H3h", frame | (0x8000 if sign else 0), *xyz) for frame, sign, xyz in q))
        t_tracks.append(b"".join((struct.pack("<B", 0x40 | frame) if frame < 64 else struct.pack("<Bh", 0, frame)) +
                               struct.pack("<3h", *xyz) if compressed else struct.pack("<4h", frame, *xyz) for frame, xyz in t))
    if compressed:
        data += struct.pack("<II", sum(map(len, q_tracks)), sum(map(len, t_tracks)))
        data += struct.pack(f"<{count}H", *map(len, q_tracks)) + struct.pack(f"<{count}H", *map(len, t_tracks))
    else:
        data += b"".join(struct.pack("<2h" if hires else "<2B", len(q), len(t)) for q, t in tracks)
    data += b"\0" * (-len(data) % 4)
    data += b"".join(q_tracks) + b"".join(t_tracks)
    return data + b"\0" * (-len(data) % 4)


def compressed_branches_fixture():
    # Cover all seven short-component flag combinations, table IDs above 127,
    # both quaternion signs, uncompressed keys and long/short translation times.
    q_tracks, t_tracks = [], []
    for mask in range(8):
        if mask == 0:
            q = struct.pack("<HB", 0x4000, 200) + struct.pack("<HB", 0xc000 | 60, 201)
        else:
            bits = sum(flag for index, flag in enumerate((0x2000, 0x1000, 0x0800)) if mask & (1 << index))
            q = b""
            for time in (0, 60):
                q += struct.pack("<H", 0x4000 | bits | time | (0x8000 if time else 0))
                for index in range(3):
                    q += struct.pack("<B", 200 + index) if mask & (1 << index) else struct.pack("<h", -4096 + index * 512)
        q_tracks.append(q)
        t_tracks.append(struct.pack("<BBBhB", 0xc0, 200, 0x80, 60, 201))
    flags = COMPRESS_TABLE | COMPRESSED_TIME | PREROTATED_ROOT
    data = struct.pack("<IIf6I", 42, flags, 1, 8, 16, 16, 0, sum(map(len, q_tracks)), sum(map(len, t_tracks)))
    data += struct.pack("<16H", *map(len, q_tracks), *map(len, t_tracks))
    data += b"".join(q_tracks) + b"".join(t_tracks)
    return data + b"\0" * (-len(data) % 4)


class AnimationTests(unittest.TestCase):
    def test_platform_and_large_count_tables_preserve_keys(self):
        for hires in (False, True):
            raw = animation_fixture(hires=hires)
            clip = parse(raw)
            self.assertEqual(clip["source_end"], len(raw))
            self.assertEqual(clip["rotation_key_count"], 9)
            self.assertFalse(clip["version_verified"])
            self.assertTrue(clip["tracks"][0]["rotation_keys"][1]["negative_w"])
        tracks = [([(i, False, (0, 0, 0)) for i in range(300)], [(0, (0, 0, 0))])]
        clip = parse(animation_fixture(count=1, hires=True, duration=5, tracks=tracks))
        self.assertEqual(clip["rotation_key_count"], 300)
        self.assertEqual(sample(clip, 2.5)[0], ([0, 0, 0, 1], [0, 0, 0]))

    def test_compressed_raw_and_lookup_short_unsigned_components(self):
        platform = parse(animation_fixture())
        raw = parse(animation_fixture(compressed=True))
        self.assertEqual(platform["tracks"], raw["tracks"])
        q_table, t_table = tables_fixture()
        clip = parse(compressed_branches_fixture(), q_table, t_table)
        self.assertEqual(clip["tracks"][0]["rotation_keys"][0]["xyz_short"], [0, 0, 11585])
        self.assertEqual(clip["tracks"][7]["rotation_keys"][0]["xyz_short"], [200, 201, 202])
        self.assertEqual(clip["tracks"][0]["translation_keys"][1]["xyz_short"], [-128, 64, 160])
        for q, t in ((None, t_table), (q_table, None), (b"wrong size", t_table)):
            with self.assertRaises(ValueError):
                parse(compressed_branches_fixture(), q, t)

    def test_authentic_sign_identity_nlerp_and_time_behavior(self):
        key = {"xyz_short": [0, 0, 0], "negative_w": True}
        self.assertEqual(rotation(key, False), [0, 0, 0, -1])
        self.assertEqual(rotation(key, True), [0, 0, 0, 1])
        value = fast_slerp([0, 0, 0, 1], [0, 0, 1, 0], 0.25)
        self.assertAlmostEqual(value[2], 1 / math.sqrt(10), places=7)
        self.assertGreater(abs(value[2] - math.sin(math.pi / 8)), 0.06)
        clip = parse(animation_fixture())
        self.assertEqual(sample(clip, 0)[1][1], [1, 0, 0])
        self.assertEqual(sample(clip, 0.5)[1][1], [1, 0.5, -1])
        self.assertEqual(sample(clip, 1)[1][1], [1, 1, -2])
        late = animation_fixture(count=1, tracks=[([(10, False, (0, 0, 0)), (60, False, (8192, 0, 0))],
                                                 [(10, (0, 0, 0)), (60, (32, 64, 96))])])
        self.assertEqual(sample(parse(late), 0)[0][1], [1, 2, 3])
        for time in (-1, 1.1, math.inf, math.nan):
            with self.assertRaises(ValueError): sample(clip, time)

    def test_all_truncation_boundaries_and_trailers_rejected(self):
        for raw in (animation_fixture(), animation_fixture(compressed=True), compressed_branches_fixture()):
            for length in range(len(raw)):
                with self.subTest(length=length), self.assertRaises(ValueError):
                    parse(raw[:length], *tables_fixture())
            with self.assertRaises(ValueError): parse(raw + b"\0\0\0\0", *tables_fixture())

    def test_unsupported_flags_counts_times_and_invalid_quaternions(self):
        raw = animation_fixture()
        for offset, fmt, value in ((4, "I", PLATFORM), (4, "I", PLATFORM | COMPRESS_TABLE | COMPRESSED_TIME | PREROTATED_ROOT),
                                   (4, "I", PLATFORM | COMPRESSED_TIME | PREROTATED_ROOT | (1 << 19)),
                                   (8, "f", math.nan), (8, "f", 0), (12, "I", 64), (16, "I", 32768),
                                   (24, "I", 1), (28, "B", 0)):
            damaged = bytearray(raw)
            struct.pack_into("<" + fmt, damaged, offset, value)
            with self.assertRaises(ValueError): parse(damaged)
        for tracks in ([([(0, False, (0, 0, 0)), (0, False, (0, 0, 0))], [(0, (0, 0, 0))])],
                       [([(16384, False, (0, 0, 0))], [(0, (0, 0, 0))])],
                       [([(0, False, (20000, 0, 0))], [(0, (0, 0, 0))])],
                       [([(0, False, (0, 0, 0))], [(-1, (0, 0, 0))])]):
            with self.assertRaises(ValueError): parse(animation_fixture(count=1, tracks=tracks))
        compressed = bytearray(animation_fixture(compressed=True))
        struct.pack_into("<I", compressed, 28, 1)
        with self.assertRaises(ValueError): parse(compressed)

    def test_animated_glb_absolute_pose_and_tick_sampling(self):
        rig, mesh, clip = parse_rig(rig_fixture()), parse_skin(skin_fixture(), "dx9"), parse(animation_fixture(duration=0.991))
        glb, summary = build(rig, mesh, clip)
        document, binary = unpack_glb(glb)
        self.assertTrue(summary["animations_imported"])
        self.assertEqual(len(document["animations"]), 1)
        for index, channel in enumerate(document["animations"][0]["channels"]):
            node = document["nodes"][channel["target"]["node"]]
            self.assertNotIn("matrix", node)
            sampler = document["animations"][0]["samplers"][channel["sampler"]]
            self.assertEqual(sampler["interpolation"], "STEP")
            times = [v[0] for v in accessor_rows(document, binary, sampler["input"])]
            self.assertTrue(all(a < b for a, b in zip(times, times[1:])))
            self.assertEqual(times[-1], clip["duration_seconds"])
            values = accessor_rows(document, binary, sampler["output"])
            for time, value in zip(times, values):
                q, t = sample_track(clip["tracks"][index // 2], time, False)
                if channel["target"]["path"] == "rotation":
                    length = math.sqrt(sum(v * v for v in q))
                    expected = [-q[0] / length, -q[1] / length, -q[2] / length, q[3] / length]
                else:
                    expected = [v * 0.0254 for v in t]
                for a, b in zip(value, expected): self.assertAlmostEqual(a, b, places=7)
        # Original skeleton update uses the clip's local pose as-is. The neutral
        # child Y offset must not be added a second time to this X translation.
        sampler = document["animations"][0]["samplers"][3]
        self.assertEqual(accessor_rows(document, binary, sampler["output"])[0], (struct.unpack("<f", struct.pack("<f", 0.0254))[0], 0, 0))
        with self.assertRaises(ValueError): build(rig, mesh, parse(animation_fixture(count=1)))
        # Reject an oversized bake before allocating a million pose arrays.
        with self.assertRaisesRegex(ValueError, "baked pose limit"):
            build(parse_rig(boundary_rig_fixture()), mesh, parse(animation_fixture(count=63, duration=16383 / 60)))

    def test_local_import_preserves_inputs_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ske, skin, clip = [root / name for name in ("source.ske", "source.skin", "source.ska")]
            for path, data in ((ske, rig_fixture()), (skin, skin_fixture()), (clip, animation_fixture())):
                path.write_bytes(data)
            package = import_files(ske, skin, root / "preview", "dx9", clip)
            self.assertEqual(package["animation"]["tracks"], parse(clip.read_bytes())["tracks"])
            original = (root / "preview/character.glb").read_bytes()
            with self.assertRaises(FileExistsError): import_files(ske, skin, root / "preview", "dx9", clip)
            self.assertEqual((root / "preview/character.glb").read_bytes(), original)
            self.assertEqual(clip.read_bytes(), animation_fixture())
            clip.write_bytes(b"bad")
            with self.assertRaises(ValueError): import_files(ske, skin, root / "bad", "dx9", clip)
            self.assertFalse((root / "bad").exists())
            with self.assertRaises(ValueError): import_files(ske, skin, root / "table-only", "dx9", q_table=clip)


if __name__ == "__main__":
    unittest.main()
