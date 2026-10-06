"""Apply a bounded authoring patch to an immutable source world."""
import hashlib
import json
from pathlib import Path

from gonk_world import encode, validate


def identity(world):
    return hashlib.sha256(encode(world)).hexdigest()


def apply_patch(world, patch):
    if patch.get('schema_version') != 1 or patch.get('source_sha256') != identity(world):
        raise ValueError('Workshop source changed; reopen the map before saving')
    name = patch.get('name')
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        raise ValueError('Map name must contain 1–100 characters')
    # Only skating annotations can change. Geometry and import provenance remain
    # attached to their source, rather than being trusted from the editor output.
    result = validate({**world, 'name': name.strip(), 'spawn': patch['spawn'],
                       'facing': patch['facing'], 'rails': patch['rails']})
    result['authoring'] = {'tool': 'gonkskate-workshop-v1', 'parent_world_sha256': identity(world),
                           'rails': 'User-authored annotations; original game rail data not extracted'}
    return result


def read_patch(path):
    path = Path(path)
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Workshop annotations exceed 4 MiB')
    return json.loads(path.read_text(encoding='utf-8'))
