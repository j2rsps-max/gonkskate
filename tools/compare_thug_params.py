"""Compare live skating overrides, then globals; ignore comments/bike values."""
import argparse
import json
from pathlib import Path
from thug_q import physics_tables, lookup


def compare(q, cfg):
    globals_, skating = physics_tables(q)
    mismatches, found = [], 0
    for p in cfg['parameters']:
        name, expected = p['name'], p['value']
        try:
            raw = lookup(name, globals_, skating)
        except KeyError:
            mismatches.append({'name': name, 'reason': 'not found in active skating/global declarations'})
            continue
        try:
            actual = float(raw)
        except ValueError:
            mismatches.append({'name': name, 'reason': 'non-scalar active value: ' + raw})
            continue
        found += 1
        if abs(float(expected)-actual) > max(1e-6, abs(float(expected))*1e-6):
            mismatches.append({'name': name, 'expected': expected, 'actual': actual})
    return {'captured_parameter_count': len(cfg['parameters']), 'found_in_physics_q': found,
            'mismatch_count': len(mismatches), 'mismatches': mismatches}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('logdir', type=Path)
    parser.add_argument('--strict', action='store_true', help='Fail on missing/changed active definitions')
    args = parser.parse_args()
    result = compare((args.root / 'external/kisak-thug/Scripts/game/skater/physics.q').read_text(),
                     json.loads((args.root / 'native/thug_adapter/config/thug_core_physics_defaults.json').read_text()))
    args.logdir.mkdir(parents=True, exist_ok=True)
    (args.logdir / 'thug-param-compare.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    # Research comparison remains nonblocking in the Windows readiness harness.
    # Strict mode is available for an adapter that requires all captured values.
    raise SystemExit(1 if args.strict and result['mismatch_count'] else 0)
