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

ROOT = Path(__file__).resolve().parents[1]


class CheckTests(unittest.TestCase):
    def test_packaged_success_and_failure_keep_assets_local(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "GonkSkate check"
            files = ("scripts/run-character-check.py", "tools/import_thug_rig.py", "tools/import_thug_skin.py",
                     "tools/import_thug_character.py", "tools/test_thug_rig.py", "tools/test_thug_character.py")
            for name in files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, path)
            ske, skin = root / "local-π.ske", root / "local-π.skin"
            ske.write_bytes(rig_fixture())
            skin.write_bytes(skin_fixture())
            raw = skin.read_bytes()
            commands = [([], 0, "UNRUN"), ([str(ske)], 1, "UNRUN"),
                        ([str(ske), str(skin)], 1, "UNRUN"),
                        ([str(ske), str(skin), "--weight-profile", "dx9"], 0, "PARSED_LOCAL_RIGGED_PREVIEW")]
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
                    forbidden = {"positions_inches", "bones", "sectors", "joints", "weights_packed", "inverse_bind_matrix", "rig", "mesh"}
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
            self.assertEqual(len(list((root / "local-characters").rglob("character.glb"))), 1)
            skin.write_bytes(b"unsupported layout")
            result = subprocess.run([sys.executable, str(root / "scripts/run-character-check.py"), str(ske), str(skin),
                                     "--weight-profile", "xbox"], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(len(list((root / "local-characters").rglob("character.glb"))), 1)


if __name__ == "__main__":
    unittest.main()
