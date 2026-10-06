#!/usr/bin/env python3
"""Open the visual authoring tool, save a private map copy and report its identity."""
import argparse
import datetime
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from godot_runtime import godot
from gonk_world import load
from project_hub import Library, save_json
from world_workshop import identity, read_patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world', type=Path, required=True)
    parser.add_argument('--autotest', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    directory = ROOT / 'logs' / ('workshop-' + stamp)
    directory.mkdir(parents=True)
    report = {'version': (ROOT / 'VERSION').read_text().strip(), 'exit_code': 0,
              'saved': False, 'cancelled': False, 'retail_assets_in_report': False}
    try:
        world = load(args.world)
        source = directory / 'private-source.json'
        save_json(source, world)
        env = os.environ.copy()
        env.update(GONK_WORLD_JSON=str(source.resolve()), GONK_WORLD_SHA=identity(world),
                   GONK_WORKSHOP_PATCH=str((directory / 'private-patch.json').resolve()),
                   GONK_WORKSHOP_RESULT=str((directory / 'editor-result.json').resolve()))
        for key, subdir in [('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache')]:
            env.setdefault(key, str(ROOT / 'bin/godot' / subdir))
        with (directory / 'editor.txt').open('w', encoding='utf-8') as output:
            command = [godot(ROOT), '--path', str(ROOT / 'playable')]
            command += ['--headless','--script','res://test_workshop.gd'] if args.autotest else ['res://workshop.tscn']
            result = subprocess.run(command, env=env, cwd=ROOT,
                                    stdout=output, stderr=subprocess.STDOUT)
        health_path = directory / 'editor-result.json'
        if not health_path.is_file():
            raise ValueError('Workshop exited without a report; return the results ZIP')
        health = json.loads(health_path.read_text())
        if result.returncode or health['failed']:
            raise ValueError('Workshop failed; see editor.txt')
        if health['saved']:
            library = Library()
            # Re-read the source so a concurrent change cannot silently attach a
            # stale patch to different collision geometry.
            item = library.save_variant(args.world, read_patch(directory / 'private-patch.json'))
            report.update(saved=True, world_filename=Path(item['path']).name,
                          rails=item['rails'], triangles=item['triangles'],
                          world_sha256=identity(load(library.map_path(item))))
            print('Saved map copy:', item['name'], flush=True)
        else:
            report['cancelled'] = True
            print('Workshop closed; source map preserved.', flush=True)
    except Exception as error:
        report.update(exit_code=1, error=str(error))
        print(str(error), file=sys.stderr)
    finally:
        save_json(directory / 'report.json', report)
        bundle = ROOT / 'logs' / ('GonkSkate-workshop-results-' + stamp + '.zip')
        with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
            # Never export the private source or annotation patch.
            for name in ['report.json', 'editor-result.json', 'editor.txt']:
                path = directory / name
                if path.is_file():
                    archive.write(path, name)
        print('Result bundle:', bundle, flush=True)
    return report['exit_code']


if __name__ == '__main__':
    sys.exit(main())
