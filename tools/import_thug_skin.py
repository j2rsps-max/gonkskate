"""Decode the inspected THUG Xbox/DX9 little-endian scene/skin stream layout.

The upstream loader reads, but does not interpret, its three version words.
This is a source-derived layout profile, not a claim that all .skin files match.
Packed weights require an explicit original Xbox or DX9 decoding profile.
Retail compatibility, textures, appearance scripts and animations are pending.
"""
import hashlib
import math
import struct

from import_thug_rig import THUG_PIN, f32

MAX_BYTES = 128 * 1024 * 1024
MAX_VERTICES = 1_000_000
WEIGHT_PROFILES = ("xbox", "dx9")


class Reader:
    def __init__(self, data):
        if len(data) > MAX_BYTES:
            raise ValueError("Skin exceeds the supported size limit")
        self.data = data
        self.offset = 0

    def read(self, fmt, label):
        size = struct.calcsize("<" + fmt)
        if size > len(self.data) - self.offset:
            raise ValueError(f"Truncated {label} at byte {self.offset}")
        values = struct.unpack_from("<" + fmt, self.data, self.offset)
        self.offset += size
        return values

    def scalar(self, fmt, label):
        return self.read(fmt, label)[0]

    def count(self, fmt, label, maximum, minimum=0):
        value = self.scalar(fmt, label)
        if not minimum <= value <= maximum:
            raise ValueError(f"Unsupported {label}: {value} at byte {self.offset}")
        return value

    def boolean(self, label):
        value = self.scalar("B", label)
        if value not in (0, 1):
            raise ValueError(f"Invalid {label} boolean")
        return bool(value)

    def floats(self, count, label):
        values = list(self.read(f"{count}f", label))
        if any(not math.isfinite(v) or abs(v) > 1_000_000 for v in values):
            raise ValueError(f"Non-finite or out-of-range {label}")
        return values


def checksum(value):
    return f"0x{value:08x}"


def chunks(values, size):
    return [values[i:i + size] for i in range(0, len(values), size)]


def decode_weights(packed, profile):
    if profile not in WEIGHT_PROFILES:
        raise ValueError("Choose the original xbox or dx9 weight profile")
    # Both formats use signed 11/11/10 bit components. Character import
    # supports nonnegative influences only; never reinterpret a sign bit.
    values = [packed & 0x7ff, (packed >> 11) & 0x7ff, packed >> 22]
    if values[0] & 0x400 or values[1] & 0x400 or values[2] & 0x200:
        raise ValueError("Negative packed skin weight is outside this character profile")
    if profile == "xbox":
        # Original CInstance::RenderShadowVolume's positive NORMPACKED3 decode.
        weights = [f32(values[0] * f32(1 / 1023)),
                   f32(values[1] * f32(1 / 1023)),
                   f32(values[2] * f32(1 / 511))]
    else:
        # Original DX9 sMesh::Initialize's explicitly signed float stream.
        weights = [values[0] / 1024, values[1] / 1024, values[2] / 512]
    if abs(sum(weights) - 1) > 0.006:
        raise ValueError("Skin weights do not sum to one within packed quantization tolerance")
    return weights + [0.0]


def triangles(strip):
    result = []
    # Strip parity advances through degenerate connector indices as well.
    # Matches DX9 sMesh::RawVertexFuckery's triangle-list conversion.
    for i in range(len(strip) - 2):
        a, b, c = strip[i:i + 3]
        if len({a, b, c}) == 3:
            result.extend((b, a, c) if i & 1 else (a, b, c))
    return result


def read_material(reader):
    start = reader.offset
    identity, name = reader.read("II", "material identifiers")
    count = reader.count("I", "material passes", 4, 1)
    cutoff = reader.count("I", "alpha cutoff", 255)
    sorted_draw = reader.boolean("sorted material")
    order = reader.floats(1, "draw order")[0]
    single_sided = reader.boolean("single-sided material")
    no_bfc = reader.boolean("no-backface-culling material")
    zbias = reader.scalar("i", "material z bias")
    grass = None
    if reader.boolean("grass material"):
        grass = {"height_inches": reader.floats(1, "grass height")[0],
                 "layers": reader.count("i", "grass layers", 1024)}
    power = reader.floats(1, "specular power")[0]
    specular = reader.floats(3, "specular color") if power > 0 else None
    passes = []
    for index in range(count):
        texture, flags = reader.read("II", "material texture and flags")
        has_color = reader.boolean("pass color")
        color = reader.floats(3, "pass color")
        alpha = reader.scalar("Q", "alpha register")
        addressing = list(reader.read("II", "UV addressing"))
        tiling = reader.floats(2, "environment tiling")
        filtering = reader.scalar("I", "filtering")
        uv_wibble = reader.floats(8, "UV wibble") if flags & 1 else None
        vc_wibble = []
        if index == 0 and flags & 2:
            for _ in range(reader.count("I", "vertex-color sequences", 4096)):
                keys = reader.count("I", "vertex-color keys", 65535)
                phase = reader.scalar("i", "vertex-color phase")
                vc_wibble.append({"phase": phase, "keys": [list(reader.read("i4B", "vertex-color key")) for _ in range(keys)]})
        texture_animation = None
        if flags & (1 << 11):
            keys = reader.count("i", "texture animation keys", 65535, 1)
            period, iterations, phase = reader.read("3i", "texture animation timing")
            texture_animation = {"period": period, "iterations": iterations, "phase": phase,
                                 "keys": [list(reader.read("II", "texture animation key")) for _ in range(keys)]}
        mip = list(reader.read("4I", "mipmap parameters"))
        passes.append({"texture_id": checksum(texture), "flags": flags, "has_color": has_color,
                       "color": color, "alpha_register": f"0x{alpha:016x}",
                       "uv_addressing": addressing, "environment_tiling": tiling,
                       "filtering": filtering, "uv_wibble": uv_wibble,
                       "vertex_color_wibble": vc_wibble, "texture_animation": texture_animation,
                       "mipmap_raw": mip})
    return {"source_id": checksum(identity), "source_name_id": checksum(name),
            "source_offset": start, "source_end": reader.offset, "alpha_cutoff": cutoff,
            "sorted": sorted_draw, "draw_order": order, "single_sided": single_sided,
            "no_backface_culling": no_bfc, "z_bias": zbias, "grass": grass,
            "specular_power": power, "specular_color": specular, "passes": passes}


def read_sector(reader, profile, material_ids):
    start = reader.offset
    identity, bone, flags, mesh_count = reader.read("IiII", "sector header")
    if mesh_count > 4096:
        raise ValueError("Too many meshes in sector")
    bbox = reader.floats(6, "sector bounds")
    sphere = reader.floats(4, "sector sphere")
    if flags & 0x00800000:
        raise ValueError("Billboard characters require a separate placement adapter")
    if flags & 0x200000:
        raise ValueError("Shadow-volume sectors are outside this character profile")
    count = reader.count("i", "sector vertices", 65535, 1)
    stride = reader.count("i", "source vertex stride", 4096)
    positions = chunks(reader.floats(count * 3, "vertex positions"), 3)
    normals = chunks(reader.floats(count * 3, "vertex normals"), 3) if flags & 4 else None
    packed = list(reader.read(f"{count}I", "packed weights")) if flags & 0x10 else None
    joints = chunks(list(reader.read(f"{count * 4}H", "bone indices")), 4) if packed is not None else None
    weights = [decode_weights(value, profile) for value in packed] if packed is not None else None
    if packed is not None and normals is None:
        raise ValueError("Weighted character requires normals, as does the original mesh initializer")
    uv_sets = reader.count("i", "UV sets", 4) if flags & 1 else 0
    uvs = chunks(reader.floats(count * 2 * uv_sets, "vertex UVs"), 2 * uv_sets) if uv_sets else None
    colors = list(reader.read(f"{count}I", "vertex colors")) if flags & 2 else None
    wibble = list(reader.read(f"{count}b", "vertex-color wibble indices")) if flags & 0x800 else None
    meshes = []
    for index in range(mesh_count):
        mesh_start = reader.offset
        bounds = reader.floats(10, "mesh sphere and bounds")
        mesh_flags, material = reader.read("II", "mesh flags and material")
        if checksum(material) not in material_ids:
            raise ValueError("Mesh references an unknown material")
        if mesh_flags & 0x800 and wibble is None:
            raise ValueError("Mesh requires a missing vertex-color wibble stream")
        lod_count = reader.count("I", "LOD index sets", 8, 1)
        lods = []
        for _ in range(lod_count):
            indices = list(reader.read(f"{reader.count('i', 'LOD indices', 65535)}H", "triangle-strip indices"))
            if any(value >= count for value in indices):
                raise ValueError("Triangle-strip vertex index outside the sector stream")
            lods.append(indices)
        # Original mesh initialization builds its vertex set from LOD zero.
        # Other LODs must only use vertices in that same set.
        if any(not set(lod).issubset(lods[0]) for lod in lods[1:]):
            raise ValueError("LOD references vertices outside the original highest-detail vertex set")
        meshes.append({"index": index, "source_offset": mesh_start, "source_end": reader.offset,
                       "source_flags": mesh_flags, "material_id": checksum(material),
                       "sphere_and_bounds_inches": bounds, "lod_strips": lods})
    return {"source_id": checksum(identity), "source_offset": start, "source_end": reader.offset,
            "bone_index": bone, "source_flags": flags, "source_vertex_stride": stride,
            "bounds_inches": bbox, "sphere_inches": sphere, "vertex_count": count,
            "positions_inches": positions, "normals": normals, "weights_packed": packed,
            "weights": weights, "joints": joints, "uv_set_count": uv_sets, "uvs": uvs,
            "colors_argb": colors, "vertex_color_wibble_indices": wibble, "meshes": meshes}


def parse(data, weight_profile):
    if weight_profile not in WEIGHT_PROFILES:
        raise ValueError("Explicit xbox or dx9 weight profile required")
    reader = Reader(data)
    versions = list(reader.read("3I", "scene version words"))
    materials = [read_material(reader) for _ in range(reader.count("I", "materials", 4096))]
    ids = [m["source_id"] for m in materials]
    seen = set()
    for material in materials:
        identity = material["source_id"]
        if identity in seen and identity != checksum(0):
            raise ValueError("Duplicate nonzero material, rejected by the original dictionary loader")
        # Original loader consumes duplicate dummy records (checksum zero),
        # retaining the first dictionary entry. Preserve every source record.
        material["dictionary_effective"] = identity not in seen
        seen.add(identity)
    materials_end = reader.offset
    sectors = []
    total_vertices = 0
    for _ in range(reader.count("i", "sectors", 4096, 1)):
        sector = read_sector(reader, weight_profile, set(ids))
        total_vertices += sector["vertex_count"]
        if total_vertices > MAX_VERTICES:
            raise ValueError("Total character vertex limit exceeded")
        sectors.append(sector)
    # Weighted character meshes do not need the rigid-object hierarchy. Its
    # native structure padding/placement will be handled separately.
    if reader.scalar("i", "rigid hierarchy count") != 0:
        raise ValueError("Rigid-object hierarchies are outside this character profile")
    if reader.offset != len(data):
        raise ValueError(f"Unexpected trailing skin data at byte {reader.offset}; layout/platform may differ")
    return {"schema_version": 1, "kind": "gonkskate-character-mesh", "source_game": "thug",
            "source_format": "thug-xbox-dx9-le-stream-layout", "weight_profile": weight_profile,
            "source_sha256": hashlib.sha256(data).hexdigest(), "source_version_words": versions,
            "version_words_verified": False, "inspected_upstream_commit": THUG_PIN,
            "materials_end": materials_end, "materials": materials, "sectors": sectors,
            "source_bytes": len(data), "source_vertex_count": total_vertices,
            "textures_imported": False, "animations_imported": False, "retail_validated": False}
