"""Import supported local map data through one validated world pipeline."""
import argparse
import hashlib
import json
from pathlib import Path

from gonk_world import encode, load, validate
from import_obj_world import import_obj
from import_skate3_scene import import_scene

FORMATS = {
    'obj': 'Triangulated XYZ OBJ; explicit inch/meter/centimeter units; generic collision metadata',
    'gonkworld': 'Existing normalized world JSON, schema 1 with inch units',
    'skate3-capture': 'Skate3Recomp .scene.jsonl with .buffers.bin and optional .gsnap (normally needed for static scenery)',
}


def detect_format(path):
    name = path.name.lower()
    if name.endswith('.scene.jsonl'):
        return 'skate3-capture'
    if path.suffix.lower() == '.obj':
        return 'obj'
    if path.suffix.lower() == '.json':
        return 'gonkworld'
    raise ValueError('No importer for this file type. Packed game/mod files need a source-specific converter. Use --list-formats for current support.')


def convert(path, *, format='auto', units=None, spawn_inches=None, facing=None,
            up_axis=None, flip_winding=False, capture_origin_meters=None,
            radius_meters=None, frame=None, buffers=None, memory=None):
    path = Path(path)
    selected = detect_format(path) if format == 'auto' else format
    if selected not in FORMATS:
        raise ValueError('Unknown importer format')
    obj_options = units is not None or up_axis is not None or flip_winding
    capture_options = any(v is not None for v in [capture_origin_meters, radius_meters, frame, buffers, memory])
    if obj_options and selected != 'obj':
        raise ValueError('--units, --up-axis and --flip-winding apply only to OBJ')
    if capture_options and selected != 'skate3-capture':
        raise ValueError('Capture options apply only to Skate scene recordings')
    if selected == 'obj':
        if units is None:
            raise ValueError('OBJ needs explicit --units inch, meter or centimeter')
        if units not in ['inch', 'meter', 'centimeter'] or (up_axis or 'y') not in ['y', 'z']:
            raise ValueError('Invalid OBJ units/up axis')
        world = import_obj(path, units, spawn_inches or [0, 0, 0], flip_winding, up_axis or 'y')
    elif selected == 'gonkworld':
        world = load(path)
    else:
        if frame is not None and (type(frame) is not int or frame < -1):
            raise ValueError('Capture frame must be -1 (last) or nonnegative')
        suffix = '.scene.jsonl'
        stem = path.name[:-len(suffix)] if path.name.lower().endswith(suffix) else path.name
        buffer_path = Path(buffers) if buffers is not None else path.with_name(stem + '.buffers.bin')
        memory_path = Path(memory) if memory is not None else path.with_name(stem + '.gsnap')
        if memory is not None and not memory_path.is_file():
            raise ValueError('Explicit memory snapshot not found')
        world = import_scene(path, buffer_path, frame=-1 if frame is None else frame,
                             radius=25 if radius_meters is None else radius_meters,
                             spawn=capture_origin_meters,
                             memory_path=memory_path if memory_path.is_file() else None)
    if spawn_inches is not None:
        world['spawn'] = spawn_inches
    if facing is not None:
        world['facing'] = facing
    world['import_pipeline'] = {'dispatcher': 'gonkskate-import-map-v1', 'format': selected}
    return validate(world)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--list-formats', action='store_true')
    parser.add_argument('--format', choices=['auto', *FORMATS], default='auto')
    parser.add_argument('--units', choices=['inch', 'meter', 'centimeter'], help='OBJ source units; never guessed')
    parser.add_argument('--spawn-inches', type=float, nargs=3, help='Spawn in output world inches, for every importer')
    parser.add_argument('--facing', type=float, nargs=3, help='Horizontal spawn direction in normalized world axes')
    parser.add_argument('--up-axis', choices=['y', 'z'], help='OBJ source up axis (default Y)')
    parser.add_argument('--flip-winding', action='store_true', help='Reverse OBJ faces')
    parser.add_argument('--capture-origin-meters', type=float, nargs=3, help='Skate capture crop/support origin in source meters; default camera')
    parser.add_argument('--radius-meters', type=float, help='Skate capture crop radius; default 25, maximum 200')
    parser.add_argument('--frame', type=int, help='Skate zero-based capture frame; default last')
    parser.add_argument('--buffers', type=Path, help='Explicit Skate recorded buffer file')
    parser.add_argument('--memory', type=Path, help='Explicit Skate memory snapshot')
    args = parser.parse_args()
    if args.list_formats:
        print(json.dumps(FORMATS, indent=2))
        return 0
    if args.source is None or args.output is None:
        parser.error('source and --output are required')
    options = vars(args).copy()
    for key in ['source', 'output', 'list_formats']:
        options.pop(key)
    try:
        if args.output.exists():
            raise ValueError('Output exists; choose a new world file')
        world = convert(args.source, **options)
        binary = encode(world)  # Check the complete native transport before saving.
        document = json.dumps(world, separators=(',', ':'), allow_nan=False) + '\n'
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as output:
            output.write(document)
    except (ValueError, OSError, KeyError, TypeError, OverflowError) as error:
        parser.exit(2, f'Import failed: {error}\n')
    print(json.dumps({'output': str(args.output), 'format': world['import_pipeline']['format'],
                      'triangles': len(world['triangles']), 'rails': len(world['rails']),
                      'native_world_sha256': hashlib.sha256(binary).hexdigest()}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
