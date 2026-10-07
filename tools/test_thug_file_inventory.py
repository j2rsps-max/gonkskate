"""Metadata-only inventory boundaries, exclusions and packaged diagnostics."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import thug_file_inventory as tool

ROOT = Path(__file__).resolve().parents[1]


class InventoryTests(unittest.TestCase):
    def test_unicode_case_and_packages_without_reading_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game = root / "Tony Hawk π"
            game.mkdir()
            for name in ("body.SKIN.XBX", "skater.ske", "body.tex.xbx", "push.ska.xbx", "skaters.pre", "unknown.bin"):
                (game / name).write_bytes(b"RETAIL_CONTENT_MUST_STAY_LOCAL")
            package = root / "Integration"
            package.mkdir()
            (package / "RUN_CHARACTER_CHECK.cmd").touch()
            (package / "synthetic.ske.xbx").write_bytes(b"fixture")
            with patch.object(Path, "open", side_effect=AssertionError("Asset contents must not be opened")):
                result = tool.inventory(root)
            self.assertTrue(result["complete"])
            self.assertEqual(result["files_counted"], 6)
            self.assertEqual(result["kind_counts"], {"ske": 1, "skin": 1, "tex": 1, "ska": 1, "archive": 1, "other": 1})
            self.assertFalse(result["source_formats_verified"] or result["character_pairs_verified"])
            self.assertEqual(result["skipped"], [{"path": "Integration", "reason": "gonkskate-package"}])
            self.assertNotIn("RETAIL_CONTENT", json.dumps(result))
            with self.assertRaisesRegex(ValueError, "GonkSkate tools folder"):
                tool.inventory(package)

    def test_links_cannot_escape_selected_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "game"
            outside = parent / "outside"
            root.mkdir(); outside.mkdir()
            (outside / "private.ske").write_bytes(b"outside")
            try:
                (root / "linked-directory").symlink_to(outside, target_is_directory=True)
                (root / "linked-file.skin").symlink_to(outside / "private.ske")
            except OSError as error:
                self.skipTest("Symlink creation unavailable: " + str(error))
            result = tool.inventory(root)
            self.assertEqual(result["files_counted"], 0)
            self.assertEqual(len(result["skipped"]), 2)
            self.assertTrue(all(item["reason"] == "link-or-reparse-point" for item in result["skipped"]))

    def test_limits_and_permission_errors_produce_incomplete_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.ske").touch(); (root / "b.skin").touch()
            with patch.object(tool, "MAX_FILES", 1):
                result = tool.inventory(root)
            self.assertTrue(result["limit_reached"])
            self.assertFalse(result["complete"])
            child = root / "locked"
            child.mkdir()
            original = os.scandir
            def guarded(folder):
                if Path(folder) == child:
                    raise PermissionError("Synthetic unreadable directory")
                return original(folder)
            with patch.object(tool.os, "scandir", side_effect=guarded):
                result = tool.inventory(root)
            self.assertFalse(result["complete"])
            self.assertEqual(result["errors"], [{"path": "locked", "error_type": "PermissionError"}])

    def test_packaged_command_preserves_files_and_returns_only_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package, game = root / "Integration π", root / "THUG π"
            game.mkdir()
            payload = b"ASSET_SECRET_NEVER_COPY_402945"
            (game / "skaters.pre").write_bytes(payload)
            for name in ("scripts/run-thug-file-check.py", "tools/thug_file_inventory.py"):
                target = package / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            for folder, status in ((game, 0), (root / "missing", 1)):
                result = subprocess.run([sys.executable, str(package / "scripts/run-thug-file-check.py"),
                    "--game-root", str(folder)], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, status, result.stdout + result.stderr)
            bundles = sorted((package / "logs").glob("GonkSkate-thug-files-results-*.zip"))
            self.assertEqual(len(bundles), 2)
            for index, bundle in enumerate(bundles):
                with zipfile.ZipFile(bundle) as archive:
                    expected = {"report.json", "file-inventory.json"} if index == 0 else {"report.json"}
                    self.assertEqual(set(archive.namelist()), expected)
                    for name in archive.namelist():
                        self.assertNotIn(payload, archive.read(name))
                    report = json.loads(archive.read("report.json"))
                    self.assertEqual(report["passed"], index == 0)
                    self.assertFalse(report["file_contents_included"])
            self.assertEqual((game / "skaters.pre").read_bytes(), payload)

    def test_cancel_creates_diagnostics_without_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            spec = importlib.util.spec_from_file_location("file_check", ROOT / "scripts/run-thug-file-check.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            root = Path(temporary)
            with patch.object(module, "ROOT", root), patch.object(module, "pick_game_directory", return_value=None), \
                    patch.object(sys, "argv", ["run-thug-file-check.py"]), patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(module.main(), 0)
            with zipfile.ZipFile(next((root / "logs").glob("*.zip"))) as archive:
                self.assertEqual(archive.namelist(), ["report.json"])
                self.assertEqual(json.loads(archive.read("report.json"))["status"], "CANCELLED_BY_USER")


if __name__ == "__main__":
    unittest.main()
