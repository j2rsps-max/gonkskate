"""Check a flat imported spawn with real THUG idle, standing ollie and landing."""
import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path

from gonk_world import encode, load

ROOT = Path(__file__).resolve().parents[1]


def check(world_path, executable, output, runner=()):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'profile': 'flat spawn / standing ollie / landing',
              'retail_geometry_in_report': False}
    try:
        world = load(world_path)
        data = encode(world)
        binary = output / 'private-world.gonkworld'
        binary.write_bytes(data)
        report.update(world_sha256=hashlib.sha256(data).hexdigest(),
                      world_name=world.get('name', 'Imported area'))
        command = [*runner, str(Path(executable).resolve()), '--pipe', '--world', str(binary.resolve())]
        inputs = ''.join(f'0 {int(30 <= frame < 45)} 0 0 0 0 0\n' for frame in range(180))
        first = subprocess.run(command, input=inputs, text=True, capture_output=True, timeout=60)
        (output / 'native.txt').write_text(first.stderr, encoding='utf-8')
        (output / 'trace.csv').write_text(first.stdout, encoding='utf-8')
        if first.returncode:
            raise ValueError(f'Native area check exited {first.returncode}; see native.txt')
        if 'UNSUPPORTED' in first.stderr:
            raise ValueError('Area reached an unsupported THUG dependency')
        rows = list(csv.DictReader(io.StringIO(first.stdout)))
        if len(rows) != 180 or not all(all(math.isfinite(float(v)) for v in row.values()) for row in rows):
            raise ValueError('Incomplete or non-finite simulation trace')
        spawn = world['spawn']
        if any(row['state'] != '0' or abs(float(row['y']) - spawn[1]) > 0.25 for row in rows[:30]):
            raise ValueError('Spawn is not supported on a flat surface; capture an open flat area or adjust spawn')
        if any(math.hypot(float(row['x']) - spawn[0], float(row['z']) - spawn[2]) > 2 for row in rows):
            raise ValueError('Spawn slides during the flat-floor check; choose a flatter capture origin')
        landings = [int(row['frame']) for row in rows if row['landed'] == '1']
        apex = max(float(row['y']) - spawn[1] for row in rows)
        if len(landings) != 1 or not 60 < apex < 66 or rows[-1]['state'] != '0' or abs(float(rows[-1]['y']) - spawn[1]) > 0.25:
            raise ValueError('Standing ollie/landing did not complete on the imported surface')
        second = subprocess.run(command, input=inputs, text=True, capture_output=True, timeout=60)
        if second.returncode or second.stdout != first.stdout:
            raise ValueError('Imported-area replay differs between identical fixed inputs')
        report.update(passed=True, frames=len(rows), apex_inches=apex, landing_frame=landings[0], deterministic=True)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
        raise
    finally:
        # The diagnostic folder contains an ephemeral world for the native
        # process, but exported reports explicitly exclude that file.
        (output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('world', type=Path)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runner', nargs='+', default=[])
    args = parser.parse_args()
    try:
        report = check(args.world, args.executable, args.output, args.runner)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(1, f'AREA_CHECK failed: {error}\n')
    print('AREA_CHECK passed: real THUG flat spawn, standing ollie, landing and exact replay')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
