#!/usr/bin/env python3
"""Capture locally installed Skate3Recomp scenery, then skate it with real THUG."""
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
from import_skate3_scene import import_scene
from test_imported_area import check as check_area


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--exe', type=Path, help='Installed Skate3Recomp executable (close its current window first)')
    source.add_argument('--scene', type=Path, help='Import an existing .scene.jsonl with companion buffers and memory snapshot')
    parser.add_argument('--radius', type=float, default=25, help='Captured area radius in meters (default 25)')
    parser.add_argument('--spawn', type=float, nargs=3, help='Override camera origin in source meters')
    parser.add_argument('--no-play', action='store_true', help='Import without launching GonkSkate')
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    log = ROOT / 'logs' / ('skate3-capture-' + stamp)
    capture = log / 'local-capture'
    capture.mkdir(parents=True)
    report = {'version': (ROOT / 'VERSION').read_text().strip(),
              'scope': 'Captured render geometry + authentic THUG physics; Skate guest physics not embedded',
              'retail_assets_in_result_zip': False}
    status = 0
    try:
        if args.exe:
            if sys.platform != 'win32':
                raise RuntimeError('Live Skate memory capture requires Windows. --scene can import an existing capture here.')
            exe = args.exe.resolve()
            if not exe.is_file():
                raise RuntimeError('Skate3Recomp executable not found. Pass its exact .exe path.')
            env = os.environ.copy()
            env['GONK_CAPTURE_EXE'] = str(exe)
            check = subprocess.check_output([
                'powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                '@(Get-Process | Where-Object { $_.Path -and $_.Path -eq $env:GONK_CAPTURE_EXE }).Count'
            ], env=env, text=True, timeout=15).strip()
            if check != '0':
                raise RuntimeError('Close the existing Skate3Recomp window first, then run this command again.')
            # These cvars are registered as CLI options by the upstream SDK.
            # No installed configuration, game files or saves are edited here.
            command = [str(exe), '--skate3_native_render_capture_hotkeys',
                       '--skate3_native_render_snapshot_min_meshes', '0',
                       '--skate3_native_render_snapshot_frames', '4',
                       '--skate3_native_render_snapshot_stride', '1',
                       '--skate3_native_render_snapshot_dir', str(capture.resolve())]
            print('Opening your installed Skate3Recomp. Enter a level and stop on an open, flat area.', flush=True)
            print('Press F10 once to capture. Wait for disk activity to finish, then quit Skate3Recomp normally.', flush=True)
            print('Capture may use several GB of local disk space. Do not upload the capture or ISO.', flush=True)
            with (log / 'reference-console.txt').open('w', encoding='utf-8') as output:
                result = subprocess.run(command, cwd=exe.parent, stdout=output, stderr=subprocess.STDOUT)
            report['reference_exit_code'] = result.returncode
            if result.returncode:
                raise RuntimeError(f'Skate3Recomp exited {result.returncode}; see reference-console.txt in the results.')
            scenes = sorted(capture.glob('*.scene.jsonl'), key=lambda p: p.stat().st_mtime_ns)
            if not scenes:
                raise RuntimeError('No scene capture appeared. This needs a Skate3Recomp build with native-render snapshot support; return the results ZIP and your release version.')
            scene = scenes[-1]
        else:
            scene = args.scene.resolve()
        stem = scene.name.removesuffix('.scene.jsonl')
        buffer = scene.with_name(stem + '.buffers.bin')
        memory = scene.with_name(stem + '.gsnap')
        if not memory.is_file():
            raise RuntimeError('Missing .gsnap companion. Static scenery needs the Windows F10 memory snapshot.')
        world = import_scene(scene, buffer, radius=args.radius, spawn=args.spawn, memory_path=memory)
        output = ROOT / 'local-worlds' / ('skate3-area-' + stamp + '.json')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(world, separators=(',', ':')) + '\n', encoding='utf-8')
        report.update({'triangles': len(world['triangles']), 'rails': len(world['rails']),
                       'world_filename': output.name, 'provenance': world['provenance']})
        print(f'Imported {len(world["triangles"])} render triangles. Local world: {output}', flush=True)
        print('Generic concrete collision; no original Skate rail/material data. Back/View or R resets after a fall.', flush=True)
        native = ROOT / ('build/thug-headless-windows/gonkskate-thug-test.exe' if sys.platform == 'win32'
                         else 'build/thug-headless/gonkskate-thug-test')
        try:
            report['area_check'] = check_area(output, native, log / 'area-check')
        finally:
            summary = log / 'area-check/summary.json'
            if summary.is_file():
                report['area_check'] = json.loads(summary.read_text(encoding='utf-8'))
        print('Area accepted: real THUG spawn, standing ollie, landing and deterministic replay.', flush=True)
        if not args.no_play:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/run-playable.py'), '--world', str(output)], cwd=ROOT)
            report['playable_exit_code'] = result.returncode
            if result.returncode:
                raise RuntimeError('GonkSkate launch/test failed; return its separate playable-results ZIP too.')
    except Exception as error:
        status = 1
        report['error'] = str(error)
        print(str(error), file=sys.stderr, flush=True)
    finally:
        report['exit_code'] = status
        (log / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        bundle = ROOT / 'logs' / ('GonkSkate-skate3-capture-results-' + stamp + '.zip')
        with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
            # Explicit allowlist: captures and world geometry stay local.
            for name in ['report.json', 'reference-console.txt', 'area-check/summary.json',
                         'area-check/native.txt', 'area-check/trace.csv']:
                file = log / name
                if file.is_file():
                    archive.write(file, name)
        print('Result bundle:', bundle, flush=True)
    return status


if __name__ == '__main__':
    sys.exit(main())
