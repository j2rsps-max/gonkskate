"""Owner command failure propagation, preservation and asset-free results."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from test_thug_character import rig_fixture, skin_fixture
from test_thug_animation import animation_fixture, compressed_branches_fixture, tables_fixture

ROOT = Path(__file__).resolve().parents[1]


class CheckTests(unittest.TestCase):
    def test_packaged_success_and_failure_keep_assets_local(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "GonkSkate check"
            files = ("scripts/run-character-check.py", "tools/import_thug_rig.py", "tools/import_thug_skin.py",
                     "tools/import_thug_character.py", "tools/test_thug_rig.py", "tools/test_thug_character.py",
                     "tools/import_thug_animation.py", "tools/test_thug_animation.py")
            for name in files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, path)
            ske, skin = root / "local-π.ske", root / "local-π.skin"
            ske.write_bytes(rig_fixture())
            skin.write_bytes(skin_fixture())
            clip = root / "clip-π.ska"
            clip.write_bytes(animation_fixture())
            raw = skin.read_bytes()
            commands = [([], 0, "UNRUN"), ([str(ske)], 1, "UNRUN"),
                        ([str(ske), str(skin)], 1, "UNRUN"),
                        ([str(ske), str(skin), "--weight-profile", "dx9"], 0, "PARSED_LOCAL_RIGGED_PREVIEW"),
                        ([str(ske), str(skin), "--weight-profile", "dx9", "--animation", str(clip)], 0, "PARSED_LOCAL_RIGGED_PREVIEW"),
                        (["--animation", str(clip)], 1, "UNRUN"),
                        ([str(ske), str(skin), "--weight-profile", "dx9", "--q-table", str(clip)], 1, "UNRUN")]
            before = set()
            for arguments, exit_code, imported in commands:
                result = subprocess.run([sys.executable, str(root / "scripts/run-character-check.py"), *arguments],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, exit_code, result.stdout + result.stderr)
                after = set((root / "logs").glob("GonkSkate-character-results-*.zip"))
                self.assertEqual(len(after - before), 1)
                with zipfile.ZipFile((after - before).pop()) as archive:
                    self.assertEqual(set(archive.namelist()), {"report.json", "format-tests.txt"})
                    report = json.loads(archive.read("report.json"))
                    self.assertEqual(report["passed"], exit_code == 0)
                    self.assertEqual(report["exit_code"], exit_code)
                    self.assertEqual(report["local_import"], imported)
                    self.assertFalse(report["complete_character_import"])
                    self.assertFalse(report["source_pair_identity_verified"])
                    self.assertGreaterEqual(report["synthetic_format_tests"]["tests_run"], 12)
                    self.assertEqual(report["animations_imported"], "--animation" in arguments and exit_code == 0)
                    forbidden = {"positions_inches", "bones", "sectors", "joints", "weights_packed", "inverse_bind_matrix", "rig", "mesh",
                                 "tracks", "rotation_keys", "translation_keys", "xyz_short"}
                    def check_keys(value):
                        if isinstance(value, dict):
                            self.assertFalse(forbidden.intersection(value))
                            for child in value.values(): check_keys(child)
                        elif isinstance(value, list):
                            for child in value: check_keys(child)
                    check_keys(report)
                before = after
                self.assertEqual(skin.read_bytes(), raw)
                self.assertEqual(ske.read_bytes(), rig_fixture())
                self.assertEqual(clip.read_bytes(), animation_fixture())
            self.assertEqual(len(list((root / "local-characters").rglob("character.glb"))), 2)
            skin.write_bytes(b"unsupported layout")
            result = subprocess.run([sys.executable, str(root / "scripts/run-character-check.py"), str(ske), str(skin),
                                     "--weight-profile", "xbox"], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(len(list((root / "local-characters").rglob("character.glb"))), 2)

    def test_missing_compression_tables_leave_diagnostic_zip(self):
        # Parser failures must produce shareable diagnostics without partial
        # derived imports or any original compressed clip/table payload.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("scripts/run-character-check.py", "tools/import_thug_rig.py", "tools/import_thug_skin.py",
                         "tools/import_thug_character.py", "tools/import_thug_animation.py", "tools/test_thug_rig.py",
                         "tools/test_thug_character.py", "tools/test_thug_animation.py"):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            ske, skin, clip = [root / name for name in ("s.ske", "s.skin", "a.ska")]
            # The eight-bone fixture triggers table lookup before count pairing.
            ske.write_bytes(rig_fixture())
            skin.write_bytes(skin_fixture())
            clip.write_bytes(compressed_branches_fixture())
            result = subprocess.run([sys.executable, str(root / "scripts/run-character-check.py"), str(ske), str(skin),
                "--weight-profile", "dx9", "--animation", str(clip)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse((root / "local-characters").exists())
            with zipfile.ZipFile(next((root / "logs").glob("*.zip"))) as archive:
                self.assertEqual(set(archive.namelist()), {"report.json", "format-tests.txt"})
                report = json.loads(archive.read("report.json"))
                self.assertFalse(report["passed"])
                self.assertIn("--q-table", report["error"])
            names = tuple(10 + 10 * i for i in range(8))
            ske.write_bytes(rig_fixture(names=names, parents=(0,) + names[:-1], flips=(0,) * 8,
                poses=[(0, 0, 0, 1, 0, 1, 0, 0)] * 8))
            q, t = root / "q48.dat", root / "t48.dat"
            for path, data in zip((q, t), tables_fixture()): path.write_bytes(data)
            result = subprocess.run([sys.executable, str(root / "scripts/run-character-check.py"), str(ske), str(skin),
                "--weight-profile", "dx9", "--animation", str(clip), "--q-table", str(q), "--t-table", str(t)],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            bundles = sorted((root / "logs").glob("*.zip"))
            self.assertEqual(len(bundles), 2)
            with zipfile.ZipFile(bundles[-1]) as archive:
                self.assertEqual(set(archive.namelist()), {"report.json", "format-tests.txt"})
                report = json.loads(archive.read("report.json"))
                self.assertTrue(report["passed"] and report["animations_imported"])
                self.assertIsInstance(report["character"]["animation"]["q_table_sha256"], str)
                self.assertNotIn("tracks", report["character"]["animation"])
            self.assertEqual(q.read_bytes(), tables_fixture()[0])
            self.assertEqual(t.read_bytes(), tables_fixture()[1])
            self.assertEqual(clip.read_bytes(), compressed_branches_fixture())


if __name__ == "__main__":
    unittest.main()
