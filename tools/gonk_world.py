"""Validated shared world schema and portable native world transport (inches)."""
import json, math, struct
from pathlib import Path

MAGIC = b'GNKWLD1\0'
MAX_TRIANGLES = 300_000
MAX_RAIL_NODES = 32_767  # Original THUG rail node numbers are signed 16-bit.

def vector(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError('Expected a three-coordinate vector')
    result = []
    for coordinate in value:
        if isinstance(coordinate, bool) or not isinstance(coordinate, (float, int)):
            raise ValueError('Coordinates must be numbers')
        coordinate = float(coordinate)
        if not math.isfinite(coordinate) or abs(coordinate) > 10_000_000:
            raise ValueError('Coordinate is non-finite or outside supported world bounds')
        result.append(struct.unpack('<f', struct.pack('<f', coordinate))[0])
    return result

def integer(value, maximum, name):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError(f'Invalid {name}')
    return value

def validate(world):
    if world.get('schema_version') != 1 or world.get('units') != 'inch':
        raise ValueError('World must use schema version 1 and inch units')
    if not isinstance(world.get('floor'), bool):
        raise ValueError('floor must be a boolean')
    triangles, rails = world.get('triangles'), world.get('rails')
    if not isinstance(triangles, list) or len(triangles) > MAX_TRIANGLES or not isinstance(rails, list):
        raise ValueError('Invalid world geometry/count')
    spawn = vector(world.get('spawn', [0, 0, 0]))
    facing = vector(world.get('facing', [0, 0, 1]))
    length = math.hypot(facing[0], facing[2])
    if abs(facing[1]) > 1e-6 or length < 1e-6:
        raise ValueError('Spawn facing must be a nonzero horizontal direction')
    facing = vector([facing[0] / length, 0, facing[2] / length])
    cleaned = []
    for triangle in triangles:
        v = triangle['vertices']
        if len(v) != 3: raise ValueError('Faces must be triangles')
        v = [vector(point) for point in v]
        a = [v[1][i]-v[0][i] for i in range(3)]
        b = [v[2][i]-v[0][i] for i in range(3)]
        normal = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
        if sum(x*x for x in normal) < 1e-12: raise ValueError('Degenerate collision triangle')
        cleaned.append({'vertices': v, 'flags': integer(triangle['flags'], 65535, 'face flags'),
                        'terrain': integer(triangle['terrain'], 59, 'terrain')})
    normalized_rails, count = [], 0
    for rail in rails:
        points = [vector(p) for p in rail['points']]
        if len(points) < 2: raise ValueError('Rails need at least two points')
        if any(a == b for a, b in zip(points, points[1:])): raise ValueError('Zero-length rail segment')
        count += len(points)
        if count > MAX_RAIL_NODES: raise ValueError('Too many THUG rail nodes')
        normalized_rails.append({'points': points, 'terrain': integer(rail['terrain'], 59, 'rail terrain')})
    if not cleaned and not world['floor']: raise ValueError('World has no collision surfaces')
    return {**world, 'spawn': spawn, 'facing': facing, 'triangles': cleaned, 'rails': normalized_rails}

def load(path):
    path = Path(path)
    if path.stat().st_size > 128*1024*1024: raise ValueError('World JSON exceeds 128 MiB')
    return validate(json.loads(path.read_text(encoding='utf-8')))

def encode(world):
    world = validate(world)
    data = bytearray(struct.pack('<8sIIII6f', MAGIC, 1, len(world['triangles']), len(world['rails']),
                                 world['floor'], *world['spawn'], *world['facing']))
    for triangle in world['triangles']:
        data += struct.pack('<9fHH', *(c for v in triangle['vertices'] for c in v), triangle['flags'], triangle['terrain'])
    for rail in world['rails']:
        data += struct.pack('<II', len(rail['points']), rail['terrain'])
        for point in rail['points']: data += struct.pack('<3f', *point)
    return bytes(data)
