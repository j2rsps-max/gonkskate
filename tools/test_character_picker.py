"""Exercise the actual Tk picker into the diagnostic/import command."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from character_file_picker import CharacterFilePicker
from test_thug_character import rig_fixture, skin_fixture
from test_thug_texture import texture_fixture

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("DISPLAY") or sys.platform == "win32", "Actual Tk test requires a display")
class PickerTests(unittest.TestCase):
    def run_check(self, root, factory):
        spec = importlib.util.spec_from_file_location("picker_check", ROOT / "scripts/run-character-check.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, "ROOT", root), patch("character_file_picker.CharacterFilePicker", side_effect=factory), \
                patch.object(sys, "argv", ["run-character-check.py", "--pick-files"]), \
                patch("sys.stdout", new_callable=io.StringIO):
            status = module.main()
        with zipfile.ZipFile(next((root / "logs").glob("GonkSkate-character-results-*.zip"))) as archive:
            self.assertEqual(set(archive.namelist()), {"report.json", "format-tests.txt"})
            report = json.loads(archive.read("report.json"))
        return status, report

    def test_actual_picker_imports_unicode_paths_with_textures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "Owner π files"
            root.mkdir()
            sources = {"skeleton": root / "local π.ske", "skin": root / "local π.skin", "textures": root / "local π.tex"}
            for name, data in (("skeleton", rig_fixture()), ("skin", skin_fixture()), ("textures", texture_fixture())):
                sources[name].write_bytes(data)
            def factory():
                picker = CharacterFilePicker()
                def select():
                    # Use actual Browse callbacks, returning paths from the
                    # native dialog boundary without a manual dialog click.
                    for name, path in sources.items():
                        with patch.object(picker.filedialog, "askopenfilename", return_value=str(path)):
                            picker.browse(name, "*")
                    picker.profile.set("THUG PC / DX9")
                    picker.submit()
                picker.root.after(0, select)
                return picker
            status, report = self.run_check(root, factory)
            self.assertEqual(status, 0)
            self.assertTrue(report["passed"] and report["textures_imported"])
            self.assertEqual(report["local_import"], "PARSED_LOCAL_RIGGED_PREVIEW")
            self.assertEqual(len(list(root.glob("local-characters/*/character.glb"))), 1)
            self.assertNotIn('"rgba"', json.dumps(report))
            self.assertEqual(sources["textures"].read_bytes(), texture_fixture())

    def test_actual_picker_cancel_creates_only_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def factory():
                picker = CharacterFilePicker()
                picker.root.after(0, picker.cancel)
                return picker
            status, report = self.run_check(root, factory)
            self.assertEqual(status, 0)
            self.assertEqual(report["local_import"], "CANCELLED_BY_USER")
            self.assertFalse((root / "local-characters").exists())

    def test_picker_missing_files_keep_dialog_open(self):
        picker = CharacterFilePicker()
        try:
            with patch.object(picker.messagebox, "showerror") as alert:
                picker.submit()
                alert.assert_called_once()
                self.assertIn("matching mesh", alert.call_args.args[1])
            self.assertTrue(picker.root.winfo_exists())
            self.assertIsNone(picker.result)
        finally:
            picker.cancel()


if __name__ == "__main__":
    unittest.main()
