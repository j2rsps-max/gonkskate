"""Exercise the editor UI through a saved copy and original THUG rail physics."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from godot_runtime import godot
from gonk_world import encode, load
from project_hub import Library, safe_diagnostic_bundle, save_json
from test_imported_area import check
from world_workshop import apply_patch, identity, read_patch

ROOT = Path(__file__).resolve().parents[1]


def annotations(world):
    return {'schema_version': 1, 'source_sha256': identity(world), 'name': 'Authored rail test',
            'spawn': world['spawn'], 'facing': world['facing'], 'rails': world['rails']}


class WorkshopTests(unittest.TestCase):
    def test_source_geometry_and_provenance_cannot_be_replaced(self):
        world = load(ROOT / 'worlds/courtyard.json')
        original = json.dumps(world, sort_keys=True)
        patch = annotations(world)
        patch.update(triangles=[], floor=True, provenance={'invalid': True})
        changed = apply_patch(world, patch)
        self.assertEqual(changed['triangles'], world['triangles'])
        self.assertEqual(changed['provenance'], world['provenance'])
        self.assertEqual(changed['floor'], world['floor'])
        self.assertEqual(json.dumps(world, sort_keys=True), original)

    def test_stale_and_invalid_annotation_rejected(self):
        world = load(ROOT / 'worlds/courtyard.json')
        patch = annotations(world)
        patch['source_sha256'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'source changed'):
            apply_patch(world, patch)
        patch = annotations(world)
        for invalid in [[], [{'points': [[0,0,0],[0,0,0]], 'terrain':3}],
                        [{'points': [[0,0,0],[0,math.nan,2]], 'terrain':3}]]:
            if not invalid:
                apply_patch(world, {**patch, 'rails': invalid})  # Removing all rails is valid.
            else:
                with self.assertRaises(ValueError):
                    apply_patch(world, {**patch, 'rails': invalid})
        with self.assertRaises(ValueError):
            apply_patch(world, {**patch, 'name': ''})

    def test_saved_variants_keep_parent_and_other_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            library = Library(directory)
            library.data['skate_executable'] = 'remembered Skate path'
            source = ROOT / 'worlds/courtyard.json'
            before = source.read_bytes()
            first = library.save_variant(source, annotations(load(source)))
            path = library.map_path(first)
            patch = annotations(load(path))
            patch['rails'] = []
            second = library.save_variant(path, patch)
            restored = Library(directory)
            self.assertEqual(restored.data['skate_executable'], 'remembered Skate path')
            self.assertEqual(restored.data['selected_map'], second['id'])
            self.assertNotEqual(first['path'], second['path'])
            self.assertEqual(len(load(path)['rails']), 2)
            self.assertEqual(load(restored.map_path(second))['rails'], [])
            self.assertEqual(source.read_bytes(), before)

    def test_export_rejects_private_annotation_patch(self):
        import zipfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('patch.json', json.dumps({'rails': []}))
            with self.assertRaises(ValueError):
                safe_diagnostic_bundle(path)


def integration(executable, engine, output, runner=()):
    output.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'version': (ROOT/'VERSION').read_text().strip(),
              'retail_assets_used': False}
    try:
        world = load(ROOT/'worlds/courtyard.json')
        world['rails'] = []
        source = output / 'private-source.json'
        save_json(source, world)
        patch_path = output / 'private-patch.json'
        result_path = output / 'editor-result.json'
        for path in [patch_path, result_path]:
            path.unlink(missing_ok=True)
        windows = bool(runner) and str(engine).endswith('.exe')
        def guest_path(path):
            path = str(Path(path).resolve())
            return 'Z:' + path if windows else path
        env = os.environ.copy()
        env.update(GONK_WORLD_JSON=guest_path(source), GONK_WORLD_SHA=identity(world),
                   GONK_WORKSHOP_PATCH=guest_path(patch_path), GONK_WORKSHOP_RESULT=guest_path(result_path))
        for key, subdir in [('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache')]:
            env.setdefault(key,str(ROOT/'bin/godot'/subdir))
        editor = subprocess.run([*runner,str(engine),'--headless','--path',guest_path(ROOT/'playable'),
                                 '--script','res://test_workshop.gd'],env=env,capture_output=True,text=True,timeout=90)
        (output/'editor.txt').write_text(editor.stdout+editor.stderr,encoding='utf-8')
        assert editor.returncode==0 and 'WORKSHOP_TEST passed' in editor.stdout, editor.stdout+editor.stderr
        health = json.loads(result_path.read_text())
        assert health['saved'] and not health['failed'] and health['rails']==1
        # Isolated settings demonstrate that the editor's actual patch travels
        # through the same save path used by the hub, without modifying a source.
        library = Library(output)
        item = library.save_variant(source,read_patch(patch_path))
        edited_path = library.map_path(item)
        edited = load(edited_path)
        assert load(source)['rails']==[]
        check(edited_path, executable, output/'area-check', runner)
        binary = output/'private-authored.gonkworld'
        binary.write_bytes(encode(edited))
        command = [*runner,str(Path(executable).resolve()),'--pipe','--world',str(binary.resolve())]
        inputs = ''.join(f'{int(30<=f<240)} {int(80<=f<95)} 0 0 0 {int(f>=95)} {int(f==280)}\n' for f in range(300))
        first = subprocess.run(command,input=inputs,capture_output=True,text=True,timeout=60)
        (output/'rail.csv').write_text(first.stdout,encoding='utf-8')
        (output/'native.txt').write_text(first.stderr,encoding='utf-8')
        assert first.returncode==0 and 'UNSUPPORTED' not in first.stderr, first.stderr
        rows = list(csv.DictReader(io.StringIO(first.stdout)))
        assert len(rows)==300 and all(all(math.isfinite(float(v)) for v in r.values()) for r in rows)
        states = [int(r['state']) for i,r in enumerate(rows[:280]) if i==0 or r['state']!=rows[i-1]['state']]
        assert states==[0,1,4,1,0], states
        rail = [r for r in rows if r['state']=='4']
        assert len(rail)>=15 and all(r['rail']=='0' and abs(float(r['y'])-144)<0.001 for r in rail)
        assert 'SelectedGrindScript:Trick_5050_FS' in first.stderr
        assert rows[280]['reset']=='1' and rows[280]['state']=='0' and rows[280]['z']=='0' and rows[280]['y']=='120'
        second = subprocess.run(command,input=inputs,capture_output=True,text=True,timeout=60)
        assert second.returncode==0 and first.stdout==second.stdout
        report.update(passed=True,editor_ui_and_controller=True,saved_copy=True,flat_spawn_check=True,
                      authentic_rail_ticks=len(rail),state_sequence=states,landing_frame=next(int(r['frame']) for r in rows if r['landed']=='1'),
                      reset_passed=True,replay_equal=True,trace_sha256=hashlib.sha256(first.stdout.encode()).hexdigest(),
                      executable_sha256=hashlib.sha256(Path(executable).read_bytes()).hexdigest())
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        save_json(output/'summary.json',report)
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integration',action='store_true')
    parser.add_argument('--executable',type=Path)
    parser.add_argument('--godot',type=Path)
    parser.add_argument('--runner',nargs='+',default=[])
    parser.add_argument('--output',type=Path,default=ROOT/'logs/workshop')
    args = parser.parse_args()
    if not unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WorkshopTests)).wasSuccessful():
        raise SystemExit(1)
    if args.integration:
        executable = args.executable or ROOT/('build/thug-headless-windows/gonkskate-thug-test.exe' if os.name=='nt' else 'build/thug-headless/gonkskate-thug-test')
        integration(executable,args.godot or godot(ROOT),args.output,args.runner)
