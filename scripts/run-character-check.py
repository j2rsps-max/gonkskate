#!/usr/bin/env python3
"""Check character formats, optionally importing one locally supplied THUG pair.

Results contain counts, hashes and test diagnostics only. Original files and
derived character meshes, rig matrices and GLBs remain in local-characters/.
"""
import argparse
import datetime
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from import_thug_character import import_files
from import_thug_skin import WEIGHT_PROFILES
from character_file_picker import choose_character_files, validate_sources
from test_thug_character import CharacterTests
from test_thug_rig import RigTests
from test_thug_animation import AnimationTests
from test_thug_texture import TextureTests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skeleton", type=Path, nargs="?")
    parser.add_argument("skin", type=Path, nargs="?")
    parser.add_argument("--weight-profile", choices=WEIGHT_PROFILES)
    parser.add_argument("--animation", type=Path, help="Matching local THUG full skeletal clip")
    parser.add_argument("--q-table", type=Path, help="Matching local Q48 compression table if required")
    parser.add_argument("--t-table", type=Path, help="Matching local T48 compression table if required")
    parser.add_argument("--textures", type=Path, help="Matching local THUG texture dictionary")
    parser.add_argument("--pick-files", action="store_true", help="Browse for actual THUG character files")
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    log = ROOT / "logs" / ("character-check-" + stamp)
    log.mkdir(parents=True)
    report = {"schema_version": 1, "scope": "THUG character format and optional local rigged preview",
              "complete_character_import": False, "playable_character_registered": False,
              "source_pair_identity_verified": False, "retail_visual_validation": "PENDING",
              "textures_imported": False, "animations_imported": False, "local_import": "UNRUN"}
    status = 0
    try:
        output = io.StringIO()
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case) for case in (RigTests, CharacterTests, AnimationTests, TextureTests))
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
        (log / "format-tests.txt").write_text(output.getvalue(), encoding="utf-8")
        report["synthetic_format_tests"] = {"passed": result.wasSuccessful(), "tests_run": result.testsRun}
        if not result.wasSuccessful():
            raise RuntimeError("Character format tests failed; see the result ZIP")
        if args.pick_files:
            if any(value is not None for value in (args.skeleton, args.skin, args.weight_profile,
                    args.animation, args.q_table, args.t_table, args.textures)):
                raise ValueError("Use the file picker or command-line paths; select all files in the picker.")
            selected = choose_character_files()
            if selected is None:
                report["local_import"] = "CANCELLED_BY_USER"
                report["passed"] = True
                print("Character import cancelled. No local character was created.", flush=True)
                return 0
            for name, value in selected.items():
                setattr(args, name, value)
        if bool(args.skeleton) != bool(args.skin):
            raise ValueError("Supply both the original skeleton and matching skin, or neither")
        if not args.skeleton and any(value is not None for value in (args.animation, args.q_table, args.t_table, args.textures)):
            raise ValueError("Animation/texture previews require the matching skeleton, skin and weight profile")
        if args.skeleton:
            if not args.weight_profile:
                raise ValueError("Select --weight-profile dx9 for the inspected PC decoder or xbox for the original Xbox decoder")
            selected = validate_sources(vars(args))
            for name, value in selected.items():
                setattr(args, name, value)
            local = ROOT / "local-characters" / ("thug-character-" + stamp)
            package = import_files(args.skeleton, args.skin, local, args.weight_profile, args.animation, args.q_table, args.t_table, args.textures)
            report["local_import"] = "PARSED_LOCAL_RIGGED_PREVIEW"
            report["character"] = {"summary": package["summary"], "preview_sha256": package["preview_sha256"],
                "rig_source_sha256": package["rig"]["source_sha256"], "skin_source_sha256": package["mesh"]["source_sha256"],
                "skin_source_version_words": package["mesh"]["source_version_words"],
                "source_format": package["mesh"]["source_format"], "upstream_commit": package["rig"]["inspected_upstream_commit"]}
            print("Local " + ("textured" if args.textures else "untextured") + " character:", local / "character.glb", flush=True)
            print("View it in a GLB-capable viewer. Confirm the body shape, scale and bone placement.", flush=True)
            if args.animation:
                report["animations_imported"] = True
                clip = package["animation"]
                report["character"]["animation"] = {key: clip[key] for key in ("source_sha256", "source_format", "source_version",
                    "version_verified", "source_flags", "duration_seconds", "bone_count", "rotation_key_count", "translation_key_count",
                    "q_table_sha256", "t_table_sha256", "bone_identity_verified", "retail_validated")}
                print("Select 'THUG local clip' in the viewer's animation controls. Preview uses original 60 Hz samples.", flush=True)
                print("Bone counts match; the original indexed clip cannot prove that this is the correct character rig.", flush=True)
            if args.textures:
                report["textures_imported"] = True
                textures = package["textures"]
                report["character"]["textures"] = {key: textures[key] for key in ("source_sha256", "source_format", "source_version",
                    "version_verified", "texture_count", "total_decoded_pixels", "retail_validated")}
                print("First-pass source textures are embedded in character.glb; original multi-pass effects remain metadata.", flush=True)
        else:
            print("PASS: asset-free skeleton, mesh, texture, animation and rigged-export format checks.", flush=True)
            print("To import actual THUG files, run RUN_CHARACTER_IMPORT.cmd and select them with Browse.", flush=True)
        report["passed"] = True
    except Exception as error:
        status = 1
        report["passed"] = False
        # Fixed diagnostics only; no file-content snippets or character arrays.
        report["error"] = str(error)
        print(str(error), file=sys.stderr, flush=True)
    finally:
        report["exit_code"] = status
        (log / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        bundle = ROOT / "logs" / ("GonkSkate-character-results-" + stamp + ".zip")
        with zipfile.ZipFile(bundle, "x", zipfile.ZIP_DEFLATED) as archive:
            for name in ("report.json", "format-tests.txt"):
                path = log / name
                if path.exists():
                    archive.write(path, name)
        print("Results ZIP:", bundle, flush=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
