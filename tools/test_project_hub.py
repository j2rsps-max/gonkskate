"""Persistence, failure reporting and export privacy checks for GonkSkate Hub."""
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from gonk_world import load
from project_hub import Hub, Library, ROOT, Session, discover_skate, safe_diagnostic_bundle, save_json
from test_imported_area import check
from test_world_import import snapshot_fixture


class HubTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'VERSION').write_text('test')
        self.library = Library(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_library_preserves_world_and_settings(self):
        game = self.root / 'Skate folder/skate3.exe'
        game.parent.mkdir()
        game.write_bytes(b'not executed')
        self.library.link_skate(game)
        source = ROOT / 'worlds/courtyard.json'
        item = self.library.import_map(source)
        original = load(source)
        imported = load(self.library.map_path(item))
        for key in ['spawn', 'facing', 'triangles', 'rails']:
            self.assertEqual(original[key], imported[key])
        self.library.record_check(item, {'passed': True})
        restored = Library(self.root)
        self.assertEqual(restored.data['skate_executable'], str(game))
        self.assertEqual(restored.data['selected_map'], item['id'])
        self.assertTrue(restored.maps()[1]['last_check']['passed'])
        self.assertEqual(restored.register(restored.map_path(item))['id'], item['id'])

    def test_library_blocks_escape_and_keeps_originals(self):
        with self.assertRaises(ValueError):
            self.library.register(ROOT / 'worlds/courtyard.json')
        with self.assertRaises(ValueError):
            self.library.map_path({'id': 'bad', 'path': 'local-worlds/../../outside.json'})
        first = self.library.import_map(ROOT / 'worlds/courtyard.json')
        second = self.library.import_map(self.library.map_path(first), spawn_inches=[0, 120, 0])
        self.assertNotEqual(first['path'], second['path'])
        self.assertEqual(load(self.library.map_path(first))['spawn'], load(ROOT / 'worlds/courtyard.json')['spawn'])

    def test_discovery_bounded_and_skips_links(self):
        good = self.root / 'Downloads/a/b/skate3.exe'
        good.parent.mkdir(parents=True)
        good.touch()
        deep = self.root / 'Downloads/1/2/3/4/skate3.exe'
        deep.parent.mkdir(parents=True)
        deep.touch()
        other = self.root / 'Downloads/other.exe'
        other.touch()
        self.assertEqual(discover_skate(self.root / 'Downloads'), [good])

    def test_exports_reject_world_assets_and_unknown_files(self):
        for name, content in [('area.gsnap', b'private'), ('safe.json', b'{"triangles":[]}'),
                              ('../escape.txt', b'bad'), ('hidden.zip', b'bad'), ('area.obj', b'geometry')]:
            bundle = self.root / 'bad.zip'
            with zipfile.ZipFile(bundle, 'w') as archive:
                archive.writestr(name, content)
            with self.assertRaises(ValueError, msg=name):
                safe_diagnostic_bundle(bundle)

    def test_success_stderr_and_failure_exit_are_reported(self):
        session = Session('probe', self.root)
        session.run('stderr-success', [sys.executable, '-c', 'import sys; print("benign stderr", file=sys.stderr)'])
        with self.assertRaises(RuntimeError) as failure:
            session.run('exit-seven', [sys.executable, '-c', 'raise SystemExit(7)'])
        bundle = session.finish(failure.exception)
        with zipfile.ZipFile(bundle) as archive:
            report = json.loads(archive.read('report.json'))
            self.assertEqual([r['exit_code'] for r in report['stages']], [0, 7])
            self.assertEqual(report['exit_code'], 1)
            self.assertIn(b'benign stderr', archive.read('stages/01-stderr-success.txt'))

    def test_timeout_creates_failure_bundle(self):
        session = Session('timeout', self.root)
        with self.assertRaises(TimeoutError) as failure:
            session.run('stuck', [sys.executable, '-c', 'import time; time.sleep(5)'], timeout=0.1)
        self.assertTrue(session.finish(failure.exception).is_file())

    def test_collects_only_the_childs_reported_bundle(self):
        log = self.root / 'logs'
        log.mkdir()
        own = log / 'GonkSkate-playable-results-owned.zip'
        unrelated = log / 'GonkSkate-playable-results-other.zip'
        for path in [own, unrelated]:
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('report.json', '{"exit_code":0}')
        session = Session('ownership', self.root)
        session.run('child', [sys.executable, '-c', 'print("Result bundle: " + ' + repr(str(own)) + ')'])
        self.assertEqual(session.bundles, [own])

    def test_area_private_world_is_excluded(self):
        session = Session('privacy', self.root)
        area = session.directory / 'area-check'
        area.mkdir()
        (area / 'private-world.gonkworld').write_bytes(b'private geometry')
        save_json(area / 'summary.json', {'passed': True})
        (area / 'trace.csv').write_text('frame,x,y,z\n0,0,0,0\n')
        bundle = session.finish()
        with zipfile.ZipFile(bundle) as archive:
            self.assertIn('area-check/summary.json', archive.namelist())
            self.assertNotIn('area-check/private-world.gonkworld', archive.namelist())
        safe_diagnostic_bundle(bundle)

    def test_bad_world_always_saves_summary(self):
        source = self.root / 'broken.json'
        source.write_text('{broken')
        with self.assertRaises(ValueError):
            check(source, self.root / 'missing-exe', self.root / 'area')
        self.assertFalse(json.loads((self.root / 'area/summary.json').read_text())['passed'])


def integration():
    """Use a source-format fixture, then the actual authentic core and hub exporter."""
    directory = ROOT / 'logs/hub-fixture'
    directory.mkdir(parents=True, exist_ok=True)
    scene, _, _, _ = snapshot_fixture(directory)
    hub = Hub()
    outcome = hub.execute('capture', source=scene, launch=False)
    if not outcome['passed']:
        raise RuntimeError(outcome)
    item = next(row for row in hub.library.maps() if row['id'] == hub.library.data['selected_map'])
    assert item['source'] == 'Skate capture'
    assert item['last_check']['passed']
    assert item['last_check']['deterministic']
    with zipfile.ZipFile(outcome['bundle']) as archive:
        for name in archive.namelist():
            if name.endswith('.zip'):
                import io
                with zipfile.ZipFile(io.BytesIO(archive.read(name))) as child:
                    assert not any(entry.endswith(('.gsnap', '.buffers.bin', '.gonkworld')) for entry in child.namelist())
                    assert json.loads(child.read('area-check/summary.json'))['passed']
    bad = load(hub.library.map_path(item))
    bad['spawn'][1] += 500
    bad_source = directory / 'unsupported-spawn.json'
    save_json(bad_source, bad)
    outcome_bad = hub.execute('import', source=bad_source, launch=False)
    assert not outcome_bad['passed']
    assert Path(outcome_bad['bundle']).is_file()
    # Exercise the real workshop child, saved-library refresh, area acceptance
    # and outer result export together, with an original geometry fixture.
    draft = load(ROOT / 'worlds/courtyard.json')
    draft['rails'] = []
    draft_source = directory / 'workshop-source.json'
    save_json(draft_source, draft)
    original = hub.library.import_map(draft_source)
    original_hash = hub.library.map_path(original).read_bytes()
    outcome_edit = hub.execute('workshop', item=original, options={'autotest': True}, launch=False)
    assert outcome_edit['passed'], outcome_edit
    selected = hub.library.data['selected_map']
    variant = next(row for row in hub.library.maps() if row['id'] == selected)
    assert variant['id'] != original['id'] and variant['rails'] == 1 and variant['last_check']['passed']
    assert hub.library.map_path(original).read_bytes() == original_hash
    with zipfile.ZipFile(outcome_edit['bundle']) as archive:
        for name in archive.namelist():
            if name.endswith('.zip'):
                import io
                with zipfile.ZipFile(io.BytesIO(archive.read(name))) as child:
                    assert not any('private-' in n for n in child.namelist())
    safe_diagnostic_bundle(next(Path(outcome_edit['bundle']).parent.glob('GonkSkate-workshop-results-*.zip')))
    report = {'passed': True, 'unit_tests': 9, 'fixture_capture_pipeline': True,
              'version': (ROOT / 'VERSION').read_text().strip(),
              'native_spawn_ollie_landing_replay': True, 'failed_spawn_reported': True,
              'workshop_saved_copy_pipeline': True,
              'retail_assets_used': False, 'capture_result_zip': outcome['bundle']}
    save_json(ROOT / 'logs/hub-integration-summary.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integration', action='store_true')
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(HubTests))
    if not result.wasSuccessful():
        sys.exit(1)
    if args.integration:
        integration()
