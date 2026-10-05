"""Import triangulated local OBJ geometry as a normalized collision world."""
import argparse, hashlib, json, math
from pathlib import Path
from gonk_world import validate

def import_obj(path, units, spawn, flip=False, up='y'):
    scale = {'inch': 1, 'meter': 1/0.0254, 'centimeter': 1/2.54}[units]
    vertices, triangles = [], []
    with Path(path).open(encoding='utf-8-sig') as source:
        for line_number, line in enumerate(source, 1):
            words = line.partition('#')[0].split()
            if not words: continue
            if words[0] == 'v':
                if len(words) != 4: raise ValueError(f'Line {line_number}: only XYZ vertices are supported')
                point = [float(v)*scale for v in words[1:]]
                if up == 'z': point = [point[0], point[2], -point[1]]
                vertices.append(point)
            elif words[0] == 'f':
                if len(words) != 4: raise ValueError(f'Line {line_number}: triangulate faces before import')
                face = []
                for word in words[1:]:
                    index = int(word.split('/')[0])
                    if index == 0: raise ValueError(f'Line {line_number}: OBJ indices cannot be zero')
                    index = index-1 if index > 0 else len(vertices)+index
                    if not 0 <= index < len(vertices): raise ValueError(f'Line {line_number}: invalid vertex index')
                    face.append(vertices[index])
                if flip: face[1], face[2] = face[2], face[1]
                triangles.append({'vertices': face, 'flags': 1, 'terrain': 1})
    return validate({'schema_version': 1, 'units': 'inch', 'name': Path(path).stem,
                     'source_game': 'local-geometry', 'floor': False, 'spawn': spawn,
                     'triangles': triangles, 'rails': [],
                     'provenance': {'importer': 'obj-v1', 'file': Path(path).name,
                                    'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                                    'source_units': units, 'source_up': up, 'flipped_winding': flip,
                                    'collision': 'geometry-derived; generic concrete; no source skating metadata'}})

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('obj', type=Path); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--units', choices=['inch','meter','centimeter'], required=True)
    p.add_argument('--spawn', type=float, nargs=3, required=True, metavar=('X','Y','Z'), help='Spawn in output inch coordinates')
    p.add_argument('--up-axis', choices=['y','z'], default='y'); p.add_argument('--flip-winding', action='store_true')
    a = p.parse_args()
    if a.output.exists(): p.error('Output exists; choose a new file')
    world = import_obj(a.obj, a.units, a.spawn, a.flip_winding, a.up_axis)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(world, separators=(',',':'))+'\n')
    print(f"Imported {len(world['triangles'])} triangles into {a.output}")
