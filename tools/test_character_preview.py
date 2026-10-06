"""Verify a synthetic rigged character GLB with a real engine importer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from import_thug_character import import_files
from test_thug_character import boundary_rig_fixture, rig_fixture, sector_fixture, skin_fixture

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", default="/workspace/tooling/godot-linux/Godot_v4.4.1-stable_linux.x86_64")
    parser.add_argument("--gltf-validator", type=Path, help="Optional separately installed Khronos gltf-validator module")
    args = parser.parse_args()
    build = ROOT / "build/character-preview-validation"
    build.mkdir(parents=True, exist_ok=True)
    skeleton = build / "synthetic.ske"
    skin = build / "synthetic.skin"
    skeleton.write_bytes(rig_fixture())
    environment = os.environ.copy()
    for key in ("XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME"):
        environment[key] = "/tmp/gonk-character-" + key.lower()
    results = []
    for index, (profile, boundary) in enumerate((("xbox", False), ("dx9", False), ("xbox", True), ("dx9", True))):
        case = profile + ("-63-bones" if boundary else "")
        skeleton.write_bytes(boundary_rig_fixture() if boundary else rig_fixture())
        skin.write_bytes(skin_fixture(sectors=[sector_fixture(identity=200 + i,
            joints=([0, 31, 62, 65535] * 6 if boundary else None)) for i in range(1 + index % 2)]))
        # Fresh directory; preserve all previous validation artifacts.
        import tempfile
        with tempfile.TemporaryDirectory(dir=build) as temporary:
            output = Path(temporary) / "character"
            package = import_files(skeleton, skin, output, profile)
            if args.gltf_validator:
                subprocess.run(["node", str(ROOT / "tools/validate_character_glb.cjs"), str(args.gltf_validator.resolve()),
                    str(output / "character.glb"), str(build / (case + "-khronos.json"))], check=True)
            report_path = build / (case + "-import.json")
            process = subprocess.run([args.godot, "--headless", "--path", str(build), "--script",
                str(ROOT / "native/character_import/tests/preview_import.gd"), "--", str(output / "character.glb"), str(report_path),
                str(package["summary"]["bone_count"])],
                env=environment, capture_output=True, text=True, timeout=60)
            (build / (case + "-godot.log")).write_text(process.stdout + process.stderr)
            if process.returncode:
                raise RuntimeError(process.stdout + process.stderr)
            report = json.loads(report_path.read_text())
            assert report["passed"] and report["actual_glb_import"] == "PASS", report
            report.update({"weight_profile": profile, "glb_sha256": package["preview_sha256"]})
            if args.gltf_validator:
                khronos = json.loads((build / (case + "-khronos.json")).read_text())
                report.update({"khronos_errors": khronos["issues"]["numErrors"], "khronos_warnings": khronos["issues"]["numWarnings"]})
            results.append(report)
    report = {"passed": True, "actual_engine": subprocess.check_output([args.godot, "--version"], env=environment, text=True).strip(),
              "neutral_and_posed_skinning": "PASS", "fixtures": results, "retail_character_validated": False,
              "khronos_gltf_validator": "PASS" if args.gltf_validator else "UNRUN",
              "importer_source_sha256": {name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
                  for name in ("import_thug_rig.py", "import_thug_skin.py", "import_thug_character.py")},
              "engine_fixture_sha256": hashlib.sha256((ROOT / "native/character_import/tests/preview_import.gd").read_bytes()).hexdigest(),
              "scope": "character-format validation; does not attach a player to the Skate frontend"}
    (build / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
