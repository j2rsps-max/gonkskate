"""Compare synthetic clip parsing/poses with exact original THUG methods."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import sys

from import_thug_animation import parse, sample
from import_thug_rig import THUG_PIN, normalized_matrix, quat_vector
from test_thug_animation import animation_fixture, compressed_branches_fixture, tables_fixture
from test_thug_rig_upstream import extract

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default="/workspace/tooling/llvm/usr/bin/clang++-19")
    parser.add_argument("--runner", nargs="+", default=[])
    args = parser.parse_args()
    if sys.platform != "win32" and not args.runner:
        parser.error("Original animation fixture requires Windows or --runner wine64")
    upstream = ROOT / "external/kisak-thug"
    pin = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    if pin != THUG_PIN:
        parser.error("Upstream differs from the inspected pin")
    if subprocess.check_output(["git", "-C", str(upstream), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        parser.error("Original source differential requires an unmodified tracked upstream checkout")
    build = ROOT / "build/animation-differential"
    build.mkdir(parents=True, exist_ok=True)
    code = build / "code"
    subprocess.run([sys.executable, str(ROOT / "tools/prepare_thug_headless.py"), str(upstream), str(code)], check=True)
    source = (upstream / "Code/Gfx/BonedAnim.cpp").read_text()
    markers = ["CBonedAnimFrameData::CBonedAnimFrameData()", "bool CBonedAnimFrameData::PostLoad(",
               "bool CBonedAnimFrameData::plat_read_stream(", "bool CBonedAnimFrameData::plat_read_compressed_stream(",
               "bool CBonedAnimFrameData::plat_dma_to_aram(", "int CBonedAnimFrameData::get_num_qkeys(",
               "int CBonedAnimFrameData::get_num_tkeys(", "bool CBonedAnimFrameData::is_hires()",
               "inline float timeDown(", "inline float transDown(", "inline float quatDown(", "inline float get_alpha(",
               "inline void get_rotation_from_key(", "inline void get_translation_from_key(",
               "inline void get_rotation_from_standard_key(", "inline void get_translation_from_standard_key(",
               "inline void interpolate_q_frame(", "inline void interpolate_t_frame(",
               "inline void interpolate_standard_q_frame(", "inline void interpolate_standard_t_frame(",
               "inline char * get_compressed_q_frame(", "inline char * get_compressed_t_frame(",
               "bool CBonedAnimFrameData::GetCompressedInterpolatedFrames(", "bool CBonedAnimFrameData::GetInterpolatedFrames("]
    # Original decoder signatures have conditional ARAM/non-ARAM definitions.
    # Extract the non-ARAM signature and omit the conditional directive between
    # that signature and its body; the method body remains verbatim.
    methods = []
    for marker in markers:
        method = extract(source, marker)
        if marker.startswith("inline char *"):
            method = method[:method.index("\n")] + "\n" + method[method.index("{"):]
        methods.append(method)
    (build / "upstream_animation_methods.inc").write_text("\n".join(methods))
    layout = "\n".join(extract(source, "struct " + name).rstrip() + ";" for name in
                        ("SBonedAnimFileHeader", "SPlatformFileHeader", "SStandardAnimFramePointers", "SHiResAnimFramePointers", "CBonedAnimCompressEntry"))
    layout += "\n" + "\n".join(line for line in source.splitlines() if line.startswith("#define nxBONEDANIMFLAGS_"))
    layout += "\nCBonedAnimCompressEntry sQTable[256];\nCBonedAnimCompressEntry sTTable[256];\n"
    (build / "upstream_animation_layout.inc").write_text(layout)
    skeleton = extract((upstream / "Code/Gfx/Skeleton.cpp").read_text(), "static void sQuatVecToMatrix(")
    (build / "upstream_animation_skeleton.inc").write_text(skeleton)
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = "/workspace/tooling/llvm/usr/lib/x86_64-linux-gnu"
    mingw = Path(os.environ.get("GONK_MINGW", "/workspace/tooling/mingw/usr"))
    gcc = mingw / "lib/gcc/x86_64-w64-mingw32/14-posix"
    options = ["-std=c++17", "-D__PLAT_GONK__", "-fms-extensions", "-fdelayed-template-parsing", "-ffp-contract=off",
               "-ffunction-sections", "-fdata-sections", "-Wno-register", "-Wno-writable-strings", "-Wno-comment",
               "-Wno-pointer-to-int-cast", "-I" + str(build), "-I" + str(code), "-static", "-pthread"]
    if sys.platform != "win32":
        options += ["--target=x86_64-w64-windows-gnu", "--sysroot=" + str(mingw / "x86_64-w64-mingw32"),
                    "-I" + str(gcc / "include/c++"), "-I" + str(gcc / "include/c++/x86_64-w64-mingw32"),
                    "-L" + str(gcc), "-B" + str(mingw / "bin")]
    exe = build / "animation-fixture.exe"
    subprocess.run([args.cxx, *options, str(ROOT / "native/thug_adapter/tests/upstream_animation_fixture.cpp"),
                    str(code / "core/math/vector.cpp"), "-Wl,--gc-sections", "-o", str(exe)], env=environment, check=True)
    qt, tt = tables_fixture()
    (build / "q-table.dat").write_bytes(qt)
    (build / "t-table.dat").write_bytes(tt)
    rng = random.Random(0x414e494d)
    total_keys, total_poses = 0, 0
    max_q, max_t, max_matrix = 0.0, 0.0, 0.0
    for case in range(27):
        if case == 24:
            raw = compressed_branches_fixture()
        elif case == 25:
            raw = animation_fixture(count=1, hires=True, duration=5,
                tracks=[([(i, bool(i % 2), (0, 0, i * 32)) for i in range(300)], [(0, (0, 0, 0))])])
        elif case == 26:
            raw = animation_fixture(count=1, tracks=[([(0, False, (16385, 0, 0)), (30, True, (-16385, 0, 0)),
                (60, False, (0, 0, 0))], [(0, (0, 0, 0)), (60, (100, -100, 200))])])
        else:
            count = [1, 3, 16, 63][case % 4]
            tracks = []
            for bone in range(count):
                frames = [0, 3, 15, 30, 45, 60] if case % 3 else [5, 15, 60]
                q = []
                for index, frame in enumerate(frames):
                    axis = [rng.uniform(-1, 1) for _ in range(3)]
                    length = math.sqrt(sum(v * v for v in axis))
                    angle = rng.uniform(-math.pi, math.pi) / 2
                    xyz = tuple(int(v / length * math.sin(angle) * 16384) for v in axis)
                    if bone == 0 and index == 0:
                        xyz = (0, 0, 0)  # Negative identity distinguishes the two original samplers.
                    q.append((frame, bool(index % 2), xyz))
                t = [(frame, tuple(rng.randint(-3000, 3000) for _ in range(3))) for frame in frames[::2]]
                tracks.append((q, t))
            raw = animation_fixture(count=count, compressed=bool(case % 2), hires=bool(case % 4 == 0), tracks=tracks)
        path = build / "synthetic.ska"
        path.write_bytes(raw)
        clip = parse(raw, qt, tt)
        times = [0, 1 / 60, 3 / 60, 5 / 60, 15 / 60, 30 / 60, 45 / 60, clip["duration_seconds"]] + [rng.random() * clip["duration_seconds"] for _ in range(8)]
        (build / "times.dat").write_bytes(struct.pack("<16f", *times))
        times = list(struct.unpack("<16f", (build / "times.dat").read_bytes()))
        lines = subprocess.check_output([*args.runner, str(exe), path.name, "q-table.dat", "t-table.dat", "times.dat"],
                                        cwd=build, env=environment, text=True, timeout=30).splitlines()
        header = lines.pop(0).split(",")
        assert list(map(int, header[1:4])) == [clip["bone_count"], clip["rotation_key_count"], clip["translation_key_count"]]
        assert float(header[4]) == clip["duration_seconds"]
        assert list(map(int, header[5:])) == [clip["q_stream_offset"], clip["t_stream_offset"]]
        expected_keys = []
        for track in clip["tracks"]:
            for key in track["rotation_keys"]:
                expected_keys.append(["q", track["bone_index"], key["frame"], int(key["negative_w"]), *key["xyz_short"]])
            for key in track["translation_keys"]:
                expected_keys.append(["t", track["bone_index"], key["frame"], *key["xyz_short"]])
        for line, expected in zip(lines, expected_keys):
            fields = line.split(",")
            assert fields[0] == expected[0] and list(map(int, fields[1:])) == expected[1:], (case, fields, expected)
        pose_lines = lines[len(expected_keys):]
        assert len(pose_lines) == len(times) * clip["bone_count"]
        for index, time in enumerate(times):
            expected = sample(clip, time)
            for bone, (q, t) in enumerate(expected):
                fields = pose_lines[index * clip["bone_count"] + bone].split(",")
                assert fields[:3] == ["pose", str(index), str(bone)]
                original = list(map(float, fields[3:]))
                qe = max(abs(a - b) for a, b in zip(original[:4], q))
                te = max(abs(a - b) for a, b in zip(original[4:7], t))
                matrix = normalized_matrix(quat_vector(q, t))
                original_matrix = normalized_matrix([original[7 + row * 4:11 + row * 4] for row in range(4)])
                me = max(abs(a - b) for a, b in zip(matrix, original_matrix))
                max_q, max_t, max_matrix = max(max_q, qe), max(max_t, te), max(max_matrix, me)
                assert qe < 1e-6 and te < 1e-5 and me < 1e-6, (case, index, bone, qe, te, me)
        total_keys += len(expected_keys)
        total_poses += len(pose_lines)
    report = {"passed": True, "upstream_commit": pin, "original_platform_and_compressed_readers": "PASS",
              "original_pose_interpolation": "PASS", "original_skeleton_local_pose_math": "PASS",
              "fixtures": 27, "decoded_keys_compared": total_keys, "bone_poses_compared": total_poses,
              "maximum_quaternion_error": max_q, "maximum_translation_error_inches": max_t,
              "maximum_local_matrix_error_meters": max_matrix, "retail_animation_validated": False,
              "custom_keys_and_partial_overlays": "unsupported, explicitly rejected",
              "execution": "Windows x64" + (" under Wine" if args.runner else ""),
              "source_method_sha256": {marker: hashlib.sha256(method.encode()).hexdigest() for marker, method in zip(markers, methods)},
              "skeleton_local_pose_source_sha256": hashlib.sha256(skeleton.encode()).hexdigest(),
              "importer_source_sha256": {name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
                  for name in ("import_thug_animation.py", "import_thug_character.py", "import_thug_rig.py")}}
    (build / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "source_method_sha256"}, indent=2))


if __name__ == "__main__":
    main()
