"""Validate decoded THUG texture formats through actual GLB engine import."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

from import_thug_character import import_files
from test_thug_character import rig_fixture, skin_fixture
from test_thug_texture import bc1_block, bc3_block, swizzle, texture_fixture, texture_record

ROOT = Path(__file__).resolve().parents[1]


def fixtures():
    palette = b"".join(bytes((0, 0, 255, 128)) for _ in range(256))
    return [
        ("argb32", texture_record(0x1234, 4, 4, 32, 0, 1, mips=[swizzle(bytes((3, 2, 1, 4)) * 16, 4, 4, 4)]), (1, 2, 3, 4)),
        ("a1r5g5b5", texture_record(0x1234, 4, 4, 16, 0, 1, mips=[swizzle(struct.pack("<16H", *([0xfc00] * 16)), 4, 4, 2)]), (255, 0, 0, 255)),
        ("palette8", texture_record(0x1234, 4, 4, 8, 0, 1, palette, [swizzle(bytes(16), 4, 4, 1)]), (255, 0, 0, 128)),
        ("dxt1", texture_record(0x1234, 4, 4, 4, 1, 1, mips=[bc1_block(0xf800, 0x07e0, 0)]), (255, 0, 0, 255)),
        ("dxt1-code2", texture_record(0x1234, 4, 4, 4, 2, 1, mips=[bc1_block(0xf800, 0x07e0, 0)]), (255, 0, 0, 255)),
        ("dxt5", texture_record(0x1234, 4, 4, 8, 5, 1, mips=[bc3_block(128, 0, 0, 0x001f, 0xffff, 0)]), (0, 0, 255, 128)),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", default="/workspace/tooling/godot-linux/Godot_v4.4.1-stable_linux.x86_64")
    parser.add_argument("--gltf-validator", type=Path)
    args = parser.parse_args()
    build = ROOT / "build/texture-preview-validation"
    build.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    for key in ("XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        env[key] = "/tmp/gonk-texture-" + key.lower()
    results = []
    for profile, record, rgba in fixtures():
        with tempfile.TemporaryDirectory(dir=build) as temporary:
            root = Path(temporary)
            ske, skin, tex = [root / name for name in ("c.ske", "c.skin", "c.tex")]
            ske.write_bytes(rig_fixture()); skin.write_bytes(skin_fixture()); tex.write_bytes(texture_fixture([record]))
            output = root / "character"
            package = import_files(ske, skin, output, "dx9", textures=tex)
            if args.gltf_validator:
                subprocess.run(["node", str(ROOT / "tools/validate_character_glb.cjs"), str(args.gltf_validator.resolve()),
                    str(output / "character.glb"), str(build / (profile + "-khronos.json"))], check=True)
            report_path = build / (profile + "-import.json")
            process = subprocess.run([args.godot, "--headless", "--path", str(build), "--script",
                str(ROOT / "native/character_import/tests/texture_import.gd"), "--", str(output / "character.glb"), "4", "4",
                ",".join(map(str, rgba)), str(report_path)], env=env, capture_output=True, text=True, timeout=60)
            (build / (profile + "-godot.log")).write_text(process.stdout + process.stderr)
            if process.returncode:
                raise RuntimeError(process.stdout + process.stderr)
            report = json.loads(report_path.read_text())
            assert report["passed"] and report["actual_texture_import"] == "PASS", report
            report.update({"profile": profile, "glb_sha256": package["preview_sha256"]})
            if args.gltf_validator:
                validation = json.loads((build / (profile + "-khronos.json")).read_text())
                report.update({"khronos_errors": validation["issues"]["numErrors"], "khronos_warnings": validation["issues"]["numWarnings"]})
            results.append(report)
    proof = {"passed": True, "actual_engine": subprocess.check_output([args.godot, "--version"], env=env, text=True).strip(),
             "embedded_texture_import_and_pixels": "PASS", "fixtures": results,
             "khronos_gltf_validator": "PASS" if args.gltf_validator else "UNRUN", "retail_texture_validated": False,
             "importer_source_sha256": {name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
                 for name in ("import_thug_texture.py", "import_thug_character.py", "import_thug_skin.py", "import_thug_rig.py")},
             "engine_fixture_sha256": hashlib.sha256((ROOT / "native/character_import/tests/texture_import.gd").read_bytes()).hexdigest(),
             "scope": "texture format/preview validation; original multi-pass effects and live frontend attachment remain pending"}
    (build / "validation.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
