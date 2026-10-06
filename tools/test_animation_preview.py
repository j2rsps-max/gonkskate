"""Validate real animated GLB import/playback and independent Khronos checks."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from import_thug_animation import sample
from import_thug_character import import_files, unit_quaternion
from import_thug_rig import f32, multiply, normalized_matrix, quat_vector
from test_thug_animation import animation_fixture, compressed_branches_fixture, tables_fixture
from test_thug_character import boundary_rig_fixture, rig_fixture, sector_fixture, skin_fixture

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", default="/workspace/tooling/godot-linux/Godot_v4.4.1-stable_linux.x86_64")
    parser.add_argument("--gltf-validator", type=Path)
    args = parser.parse_args()
    build = ROOT / "build/animation-preview-validation"
    build.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    for key in ("XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        env[key] = "/tmp/gonk-animation-" + key.lower()
    results = []
    for index, profile in enumerate(("platform", "hires-counts", "compressed-raw", "compressed-tables", "63-bones")):
        with tempfile.TemporaryDirectory(dir=build) as temporary:
            root = Path(temporary)
            count = 63 if profile == "63-bones" else 8 if profile == "compressed-tables" else 3
            if count == 8:
                names = tuple(10 + 10 * i for i in range(count))
                rig = rig_fixture(names=names, parents=(0,) + names[:-1], flips=(0,) * count,
                    poses=[(0, 0, 0, 1, 0, 1, 0, 0)] * count)
            else:
                rig = boundary_rig_fixture() if count == 63 else rig_fixture()
            ske, skin, clip = [root / name for name in ("synthetic.ske", "synthetic.skin", "synthetic.ska")]
            ske.write_bytes(rig)
            skin.write_bytes(skin_fixture(sectors=[sector_fixture(joints=([0, 31, 62, 65535] * 6 if count == 63 else None))]))
            clip.write_bytes(compressed_branches_fixture() if count == 8 else animation_fixture(count=count,
                compressed=profile == "compressed-raw", hires=profile == "hires-counts", duration=0.991 if index % 2 else 1))
            q, t = root / "q.dat", root / "t.dat"
            for path, data in zip((q, t), tables_fixture()): path.write_bytes(data)
            output = root / "character"
            package = import_files(ske, skin, output, "dx9" if index % 2 else "xbox", clip, q, t)
            animation = package["animation"]
            samples = []
            # Exact source ticks, between-tick STEP behavior, endpoint, and
            # reverse/random seeking (not just monotonic preview playback).
            for seconds in (0, 0.25, 0.5, 0.501, animation["duration_seconds"], 0.1, 0.107, 0.75):
                # Source time and GLB keys are float32. Avoid testing a double
                # 1.5 ns before an exact float32 key against engine tolerances.
                seconds = f32(seconds)
                baked = [f32(i / 60) for i in range(math.ceil(animation["duration_seconds"] * 60))]
                times = [time for time in baked if time < animation["duration_seconds"]]
                times.append(animation["duration_seconds"])
                held = max(time for time in times if time <= seconds)
                matrices = []
                for bone, (qv, tv) in zip(package["rig"]["bones"], sample(animation, held)):
                    local = quat_vector(unit_quaternion(qv), tv)
                    parent = bone["parent_index"]
                    matrices.append(multiply(local, matrices[parent]) if parent is not None else local)
                samples.append({"time": seconds, "held_source_time": held,
                                "global_bone_matrices": [normalized_matrix(value) for value in matrices]})
            expectation = root / "expected.json"
            expectation.write_text(json.dumps({"samples": samples,
                "inverse_bind_matrices": [bone["inverse_bind_matrix"] for bone in package["rig"]["bones"]]}))
            if args.gltf_validator:
                subprocess.run(["node", str(ROOT / "tools/validate_character_glb.cjs"), str(args.gltf_validator.resolve()),
                    str(output / "character.glb"), str(build / (profile + "-khronos.json"))], check=True)
            report_path = build / (profile + "-playback.json")
            process = subprocess.run([args.godot, "--headless", "--path", str(build), "--script",
                str(ROOT / "native/character_import/tests/animation_import.gd"), "--", str(output / "character.glb"),
                str(expectation), str(report_path)], env=env, capture_output=True, text=True, timeout=60)
            (build / (profile + "-godot.log")).write_text(process.stdout + process.stderr)
            if process.returncode:
                raise RuntimeError(process.stdout + process.stderr)
            report = json.loads(report_path.read_text())
            assert report["passed"] and report["actual_animation_playback"] == "PASS", report
            report.update({"profile": profile, "glb_sha256": package["preview_sha256"]})
            if args.gltf_validator:
                validation = json.loads((build / (profile + "-khronos.json")).read_text())
                report.update({"khronos_errors": validation["issues"]["numErrors"], "khronos_warnings": validation["issues"]["numWarnings"]})
            results.append(report)
    proof = {"passed": True, "actual_engine": subprocess.check_output([args.godot, "--version"], env=env, text=True).strip(),
             "original_clip_playback_and_deformation": "PASS", "fixtures": results, "engine_animation_bake_rate": 60,
             "khronos_gltf_validator": "PASS" if args.gltf_validator else "UNRUN", "retail_animation_validated": False,
             "importer_source_sha256": {name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
                 for name in ("import_thug_animation.py", "import_thug_character.py", "import_thug_rig.py", "import_thug_skin.py")},
             "engine_fixture_sha256": hashlib.sha256((ROOT / "native/character_import/tests/animation_import.gd").read_bytes()).hexdigest(),
             "scope": "animation format/preview validation; live frontend character attachment remains pending"}
    (build / "validation.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
