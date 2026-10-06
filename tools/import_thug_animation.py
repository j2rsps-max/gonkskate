"""Read THUG little-endian full skeletal clips and sample the original pose math.

Supports platform short keys and table-compressed keys, with optional local
Q48/T48 tables. Partial overlays, custom events and high-resolution camera or
object clips need separate adapters. Original and derived clips stay local.
"""
import argparse
from bisect import bisect_left
import hashlib
import json
import math
from pathlib import Path
import struct

from import_thug_rig import MAX_BONES, THUG_PIN, dot, f32

PLATFORM = 1 << 28
COMPRESSED_TIME = 1 << 26
PREROTATED_ROOT = 1 << 25
COMPRESS_TABLE = 1 << 23
HIRES_COUNTS = 1 << 22
CUSTOM_60 = 1 << 21
SUPPORTED_FLAGS = PLATFORM | COMPRESSED_TIME | PREROTATED_ROOT | COMPRESS_TABLE | HIRES_COUNTS | CUSTOM_60
MAX_BYTES = 16 * 1024 * 1024
MAX_KEYS = 32767  # Original CBonedAnimFrameData stores each total in a short.
MAX_DURATION = 16383 / 60
MAX_BAKED_POSES = 1_000_000


class Reader:
    def __init__(self, data):
        if len(data) > MAX_BYTES:
            raise ValueError("Animation exceeds the supported size limit")
        self.data, self.offset = data, 0

    def read(self, fmt):
        size = struct.calcsize("<" + fmt)
        if size > len(self.data) - self.offset:
            raise ValueError(f"Truncated animation at byte {self.offset}")
        values = struct.unpack_from("<" + fmt, self.data, self.offset)
        self.offset += size
        return values

    def align(self):
        self.read(f"{-self.offset % 4}s")

    def block(self, size):
        return self.read(f"{size}s")[0]


def table(data, label):
    if data is None:
        return None
    if len(data) != 256 * 8:
        raise ValueError(f"{label} table must contain the original 256 four-short entries (2048 bytes)")
    return [list(struct.unpack_from("<4h", data, index * 8)) for index in range(256)]


def lookup(entries, index, label):
    if entries is None:
        raise ValueError(f"Clip uses a {label} lookup; supply the matching local --{label.lower()}-table")
    return entries[index][:3]


def q_key(reader, compressed=False, entries=None):
    bits = reader.read("H")[0]
    sign = bool(bits & 0x8000)
    if compressed:
        timestamp = bits & 0x3fff
        if bits & 0x4000:
            timestamp &= 0x07ff
            if not bits & 0x3800:
                xyz = lookup(entries, reader.read("B")[0], "Q")
            else:
                # The original reader uses unsigned bytes for short components.
                xyz = [reader.read("B" if bits & flag else "h")[0] for flag in (0x2000, 0x1000, 0x0800)]
        else:
            xyz = list(reader.read("3h"))
    else:
        timestamp = bits & 0x7fff
        # Original CAnimQKey::timestamp is a signed 15-bit field.
        if timestamp & 0x4000:
            timestamp -= 0x8000
        xyz = list(reader.read("3h"))
    return {"frame": timestamp, "negative_w": sign, "xyz_short": xyz}


def t_key(reader, compressed=False, entries=None):
    if compressed:
        flags = reader.read("B")[0]
        timestamp = flags & 0x3f if flags & 0x40 else reader.read("h")[0]
        xyz = lookup(entries, reader.read("B")[0], "T") if flags & 0x80 else list(reader.read("3h"))
    else:
        timestamp, *xyz = reader.read("4h")
    return {"frame": timestamp, "xyz_short": xyz}


def validate_track(keys, rotation):
    if not keys:
        raise ValueError("Full clips require nonempty rotation and translation tracks for every bone")
    previous = -1
    for key in keys:
        frame = key["frame"]
        if not previous < frame <= 16383:
            raise ValueError("Clip key times must be nonnegative, strictly increasing and within the original timestamp bounds")
        previous = frame
        if rotation and sum((v / 16384) ** 2 for v in key["xyz_short"]) > 1.001:
            raise ValueError("Clip quaternion exceeds the supported unit-quaternion quantization bounds")


def parse(data, q_table=None, t_table=None):
    reader = Reader(data)
    version, flags, duration = reader.read("IIf")
    if flags & ~SUPPORTED_FLAGS:
        raise ValueError("Unsupported animation flags: partial overlays, custom/object/camera/cutscene profiles need their original adapters")
    if flags & (COMPRESSED_TIME | PREROTATED_ROOT) != COMPRESSED_TIME | PREROTATED_ROOT:
        raise ValueError("THUG clips require frame timestamps and prerotated roots")
    if bool(flags & PLATFORM) == bool(flags & COMPRESS_TABLE):
        raise ValueError("Choose exactly one original platform or table-compressed clip encoding")
    if not math.isfinite(duration) or not 0 < duration <= MAX_DURATION:
        raise ValueError("Animation duration is non-finite or outside the supported timestamp range")
    count, q_total, t_total, custom = reader.read("4I")
    if not 1 <= count <= MAX_BONES or not count <= q_total <= MAX_KEYS or not count <= t_total <= MAX_KEYS:
        raise ValueError("Animation bone/key counts exceed the original full-clip bounds")
    if custom:
        raise ValueError("Custom animation events are not supported; choose a full skeletal clip without custom keys")
    q_entries, t_entries = table(q_table, "Q48"), table(t_table, "T48")
    compressed = bool(flags & COMPRESS_TABLE)
    if compressed:
        q_bytes, t_bytes = reader.read("II")
        q_sizes = reader.read(f"{count}H")
        t_sizes = reader.read(f"{count}H")
        if sum(q_sizes) != q_bytes or sum(t_sizes) != t_bytes:
            raise ValueError("Compressed allocation sizes disagree with the per-bone track sizes")
        reader.align()
        q_start = reader.offset
        q_reader = Reader(reader.block(q_bytes))
        t_start = reader.offset
        t_reader = Reader(reader.block(t_bytes))
        rotations, translations = [], []
        for sizes, source, decoder, entries, tracks in ((q_sizes, q_reader, q_key, q_entries, rotations),
                                                       (t_sizes, t_reader, t_key, t_entries, translations)):
            total = 0
            for size in sizes:
                track = Reader(source.block(size))
                keys = []
                while track.offset < size:
                    if total >= MAX_KEYS:
                        raise ValueError("Decoded animation key limit exceeded")
                    keys.append(decoder(track, True, entries))
                    total += 1
                tracks.append(keys)
        if sum(map(len, rotations)) != q_total or sum(map(len, translations)) != t_total:
            raise ValueError("Compressed decoded key counts disagree with the header")
    else:
        counts = [reader.read("2h" if flags & HIRES_COUNTS else "2B") for _ in range(count)]
        if any(q < 1 or t < 1 for q, t in counts) or sum(q for q, _ in counts) != q_total or sum(t for _, t in counts) != t_total:
            raise ValueError("Platform per-bone key counts disagree with the full-clip header")
        reader.align()
        q_start = reader.offset
        rotations = [[q_key(reader) for _ in range(q)] for q, _ in counts]
        t_start = reader.offset
        translations = [[t_key(reader) for _ in range(t)] for _, t in counts]
    reader.align()
    if reader.offset != len(data):
        raise ValueError("Unexpected data after animation tracks")
    for keys in rotations:
        validate_track(keys, True)
    for keys in translations:
        validate_track(keys, False)
    tracks = [{"bone_index": index, "rotation_keys": q, "translation_keys": t}
              for index, (q, t) in enumerate(zip(rotations, translations))]
    return {"schema_version": 1, "kind": "gonkskate-thug-animation", "source_game": "thug",
            "source_format": "bonedanim-table-short-le" if compressed else "bonedanim-platform-short-le",
            "source_version": version, "version_verified": False, "source_flags": flags,
            "source_sha256": hashlib.sha256(data).hexdigest(), "inspected_upstream_commit": THUG_PIN,
            "duration_seconds": duration, "timestamp_rate": 60, "bone_count": count,
            "rotation_key_count": q_total, "translation_key_count": t_total, "custom_key_count": 0,
            "q_stream_offset": q_start, "t_stream_offset": t_start, "source_end": reader.offset,
            "q_table_sha256": hashlib.sha256(q_table).hexdigest() if q_table is not None else None,
            "t_table_sha256": hashlib.sha256(t_table).hexdigest() if t_table is not None else None,
            "pose_semantics": "absolute bone-local rotation/translation, not neutral-pose deltas",
            "rotation_interpolation": "THUG FastSlerp: shortest-path normalized linear interpolation",
            "bone_identity_verified": False, "retail_validated": False, "tracks": tracks}


def rotation(key, compressed):
    # Compressed GetInterpolatedFrames uses a different identity optimization:
    # zero XYZ returns positive identity even when the encoded W sign is set.
    xyz = [v / 16384 for v in key["xyz_short"]]
    if compressed and not any(xyz):
        return [0.0, 0.0, 0.0, 1.0]
    remaining = 1.0
    for value in xyz:
        remaining = f32(remaining - f32(value * value))
    w = f32(math.sqrt(max(remaining, 0.0)))
    return xyz + [-w if key["negative_w"] else w]


def lerp(a, b, alpha):
    return [f32(x + f32(f32(y - x) * alpha)) for x, y in zip(a, b)]


def fast_slerp(a, b, alpha):
    if dot(a, b) < 0:
        b = [-v for v in b]
    value = lerp(a, b, alpha)
    reciprocal = f32(1 / f32(math.sqrt(dot(value, value))))
    return [f32(v * reciprocal) for v in value]


def bracket(keys, frame):
    # Inclusive scan selects the preceding pair at an exact key time. Before
    # the first key, the original scan reaches the last key (not a clamp).
    index = bisect_left(keys, frame, key=lambda key: key["frame"])
    if index == 0 and frame < keys[0]["frame"] or index >= len(keys) or len(keys) == 1:
        return keys[-1], keys[-1], 0.0
    index = max(0, index - 1)
    a, b = keys[index], keys[index + 1]
    alpha = f32(f32(frame - a["frame"]) / f32(b["frame"] - a["frame"]))
    return a, b, alpha


def sample_track(track, seconds, compressed):
    frame = f32(f32(seconds) * 60.0)
    a, b, alpha = bracket(track["rotation_keys"], frame)
    qa, qb = rotation(a, compressed), rotation(b, compressed)
    q = qa if alpha == 0 else qb if alpha == 1 else fast_slerp(qa, qb, alpha)
    a, b, alpha = bracket(track["translation_keys"], frame)
    ta, tb = [v / 32 for v in a["xyz_short"]], [v / 32 for v in b["xyz_short"]]
    t = ta if alpha == 0 else tb if alpha == 1 else lerp(ta, tb, alpha)
    return q, t


def sample(clip, seconds):
    if not math.isfinite(seconds) or not 0 <= seconds <= clip["duration_seconds"]:
        raise ValueError("Sample time must be finite and within the clip duration")
    return [sample_track(track, seconds, bool(clip["source_flags"] & COMPRESS_TABLE)) for track in clip["tracks"]]


def read_clip(path, q_table=None, t_table=None):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Animation exceeds the supported size limit")
    tables = []
    for item in (q_table, t_table):
        if item is not None and Path(item).stat().st_size != 2048:
            raise ValueError("Animation compression tables must be 2048 bytes")
        tables.append(Path(item).read_bytes() if item is not None else None)
    return parse(path.read_bytes(), *tables)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clip", type=Path)
    parser.add_argument("--q-table", type=Path)
    parser.add_argument("--t-table", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        clip = read_clip(args.clip, args.q_table, args.t_table)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(clip, output, indent=2, allow_nan=False)
            output.write("\n")
    except (ValueError, OSError) as error:
        parser.exit(1, f"Animation import failed: {error}\n")
    print(f"Imported {clip['bone_count']} indexed bone tracks, {clip['duration_seconds']:.3f} seconds")


if __name__ == "__main__":
    main()
