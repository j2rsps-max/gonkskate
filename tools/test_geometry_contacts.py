"""Reproduce real THUG bonks and edge drops using original synthetic geometry."""
import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path

from gonk_world import encode

ROOT = Path(__file__).resolve().parents[1]


def fixtures():
    wall = {'schema_version': 1, 'units': 'inch', 'name': 'Synthetic wall contact',
            'floor': True, 'spawn': [0, 0, 0], 'facing': [0, 0, 1], 'rails': [],
            'triangles': [
                {'vertices': [[-1000, 0, 650], [-1000, 400, 650], [1000, 0, 650]], 'flags': 1, 'terrain': 1},
                {'vertices': [[1000, 0, 650], [-1000, 400, 650], [1000, 400, 650]], 'flags': 1, 'terrain': 1}]}
    ledge = {'schema_version': 1, 'units': 'inch', 'name': 'Synthetic raised finite ledge',
             'floor': True, 'spawn': [0, 120, 0], 'facing': [0, 0, 1], 'rails': [],
             'triangles': [
                 {'vertices': [[-1000, 120, -1000], [-1000, 120, 650], [1000, 120, -1000]], 'flags': 1, 'terrain': 1},
                 {'vertices': [[1000, 120, -1000], [-1000, 120, 650], [1000, 120, 650]], 'flags': 1, 'terrain': 1}]}
    def inputs(ollie=False, grind=False):
        return ''.join(f'{int(i >= 30 and i < 300)} {int(ollie and 90 <= i < 105)} 0 0 0 {int(grind)} {int(i == 320)}\n'
                       for i in range(360))
    return {'ground-bonk': (wall, inputs(), 'Flail'),
            'air-bonk-held-grind': (wall, inputs(True, True), 'PlayBonkSound'),
            'ground-wallpush-held-grind': (wall, inputs(False, True), 'WallPush'),
            'edge-drop-held-grind': (ledge, inputs(False, True), 'GroundGone')}


def verify(executable, output, runner=(), expect_old_failures=False):
    output.mkdir(parents=True, exist_ok=True)
    summary = {'passed': False, 'retail_assets_used': False, 'cases': {},
               'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest()}
    for name, (world, inputs, dependency) in fixtures().items():
        binary = output / (name + '.gonkworld')
        binary.write_bytes(encode(world))
        command = [*runner, str(executable.resolve()), '--pipe', '--world', str(binary.resolve())]
        result = subprocess.run(command, input=inputs, text=True, capture_output=True, timeout=60)
        (output / (name + '.csv')).write_text(result.stdout, encoding='utf-8')
        (output / (name + '.log')).write_text(result.stderr, encoding='utf-8')
        if expect_old_failures:
            assert result.returncode == 3 and 'UNSUPPORTED' in result.stderr, (name, result.stderr)
            summary['cases'][name] = {'old_failure_reproduced': True,
                                     'diagnostic': '\n'.join(line for line in result.stderr.splitlines() if line.startswith('UNSUPPORTED'))}
            continue
        assert result.returncode == 0 and 'UNSUPPORTED' not in result.stderr, (name, result.stderr)
        assert dependency in result.stderr, (name, 'fixture did not reach intended dependency', result.stderr)
        rows = [{key: float(value) for key, value in row.items()} for row in csv.DictReader(io.StringIO(result.stdout))]
        assert len(rows) == 360 and all(all(math.isfinite(v) for v in row.values()) for row in rows)
        assert all(r['rail'] == -1 and r['state'] in [0, 1] for r in rows), name
        assert rows[320]['reset'] == 1 and rows[320]['state'] == 0 and abs(rows[320]['y'] - world['spawn'][1]) < 0.01
        assert abs(rows[320]['x']) < 0.01 and abs(rows[320]['z']) < 0.01, 'Reset did not restore spawn'
        if name.startswith('ground-'):
            assert max(r['z'] for r in rows) <= 651, 'Passed through vertical wall'
            assert any(r['vz'] < 0 for r in rows), 'Original wall response did not reverse motion'
        if name.startswith('air-'):
            assert any(r['state'] == 1 for r in rows) and any(r['landed'] for r in rows)
            assert max(r['z'] for r in rows) <= 651, 'Airborne motion passed through wall'
        if name.startswith('edge-'):
            assert any(r['state'] == 1 and r['vy'] < 0 for r in rows)
            assert any(r['landed'] and 0 <= r['y'] <= 1 for r in rows), 'Did not land after dropping off ledge'
        replay = subprocess.run(command, input=inputs, text=True, capture_output=True, timeout=60)
        assert replay.returncode == 0 and replay.stdout == result.stdout, 'Contact replay differs'
        summary['cases'][name] = {'frames': len(rows), 'dependency': dependency,
                                 'replay_equal': True, 'reset_passed': True}
    summary['passed'] = True
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'logs/geometry-contacts')
    parser.add_argument('--runner', nargs='+', default=[])
    parser.add_argument('--expect-old-failures', action='store_true')
    args = parser.parse_args()
    verify(args.executable, args.output, args.runner, args.expect_old_failures)
