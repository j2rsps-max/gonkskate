"""Unified import routing, unit boundaries, preservation and safe CLI failures."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from gonk_world import encode, load
from import_map import convert, detect_format
from test_world_import import snapshot_fixture

ROOT = Path(__file__).resolve().parents[1]


class DispatcherTests(unittest.TestCase):
    def test_existing_world_preserves_collision_and_rails(self):
        path = ROOT / 'worlds/courtyard.json'
        self.assertEqual(encode(convert(path)), encode(load(path)))
        world = convert(path, spawn_inches=[5, 120, 6], facing=[2, 0, 0])
        self.assertEqual(world['spawn'], [5, 120, 6])
        self.assertEqual(world['facing'], [1, 0, 0])
        self.assertEqual(world['rails'], load(path)['rails'])

    def test_obj_requires_source_units_and_consistent_output_spawn(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'MAP.OBJ'
            source.write_text('v -1 0 -1\nv -1 0 1\nv 1 0 -1\nf 1 2 3\n')
            with self.assertRaisesRegex(ValueError, 'explicit --units'):
                convert(source)
            world = convert(source, units='meter', spawn_inches=[10, 0, 20])
            self.assertEqual(world['spawn'], [10, 0, 20])
            self.assertAlmostEqual(world['triangles'][0]['vertices'][0][0], -39.37008, places=4)
            with self.assertRaisesRegex(ValueError, 'Capture options'):
                convert(source, units='meter', capture_origin_meters=[0, 0, 0])

    def test_skate_capture_companions_and_unit_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            scene, buffers, memory, _ = snapshot_fixture(Path(directory))
            world = convert(scene, capture_origin_meters=[10, 5, 20])
            self.assertEqual(len(world['triangles']), 2)
            self.assertEqual(world['spawn'], [0, 0, 0])
            self.assertAlmostEqual(world['provenance']['source_origin_meters'][1], 2)
            self.assertEqual(convert(scene, spawn_inches=[5, 0, 0])['spawn'], [5, 0, 0])
            renamed = scene.with_name('fixture.SCENE.JSONL')
            scene.rename(renamed)
            scene = renamed
            self.assertEqual(len(convert(scene)['triangles']), 2)
            with self.assertRaisesRegex(ValueError, 'only to OBJ'):
                convert(scene, units='meter')
            with self.assertRaisesRegex(ValueError, 'snapshot not found'):
                convert(scene, memory=Path(directory) / 'missing.gsnap')
            with self.assertRaisesRegex(ValueError, 'frame must'):
                convert(scene, frame=-2)

    def test_unimplemented_mod_formats_are_not_claimed_supported(self):
        for suffix in ['.zip', '.pak', '.unity3d', '.big', '.dat', '.fbx']:
            with self.assertRaisesRegex(ValueError, 'No importer'):
                detect_format(Path('mod' + suffix))

    def test_cli_does_not_overwrite_and_rejects_options_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'world.json'
            command = [sys.executable, str(ROOT / 'tools/import_map.py'), str(ROOT / 'worlds/courtyard.json'), '--output', str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = output.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(output.read_bytes(), original)
            output.unlink()
            invalid = subprocess.run(command + ['--units', 'meter'], capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 2)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
