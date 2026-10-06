"""Pair a local THUG SKE and skin stream into a rigged, untextured GLB preview.

Source data and normalized preview remain local. This does not register a
playable character or invent animation, texture or appearance compatibility.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct

from import_thug_rig import MAX_BONES, parse as parse_rig
from import_thug_skin import MAX_BYTES, MAX_VERTICES, WEIGHT_PROFILES, parse as parse_skin, triangles
from import_thug_animation import COMPRESS_TABLE, MAX_BAKED_POSES, f32, read_clip, sample_track
from import_thug_texture import MAX_BYTES as MAX_TEXTURE_BYTES, metadata as texture_metadata, parse as parse_textures, png


class Glb:
    def __init__(self):
        self.binary = bytearray()
        self.document = {"asset": {"version": "2.0", "generator": "GonkSkate THUG character importer v1"},
                         "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [], "meshes": [],
                         "skins": [], "materials": [], "textures": [], "images": [], "samplers": [],
                         "bufferViews": [], "accessors": []}

    def blob(self, data):
        if len(self.binary) + len(data) + 4 > MAX_BYTES:
            raise ValueError("Normalized character binary exceeds the supported size limit")
        while len(self.binary) % 4:
            self.binary.append(0)
        offset = len(self.binary)
        self.binary.extend(data)
        index = len(self.document["bufferViews"])
        self.document["bufferViews"].append({"buffer": 0, "byteOffset": offset, "byteLength": len(data)})
        return index

    def attribute(self, rows, fmt, component, kind, bounds=False, target=None):
        if len(self.binary) + len(rows) * struct.calcsize("<" + fmt) + 4 > MAX_BYTES:
            raise ValueError("Normalized character binary exceeds the supported size limit")
        while len(self.binary) % 4:
            self.binary.append(0)
        offset = len(self.binary)
        for row in rows:
            self.binary.extend(struct.pack("<" + fmt, *row))
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(self.binary) - offset}
        if target:
            view["target"] = target
        view_index = len(self.document["bufferViews"])
        self.document["bufferViews"].append(view)
        accessor = {"bufferView": view_index, "componentType": component, "count": len(rows), "type": kind}
        if bounds:
            accessor["min"] = [min(row[i] for row in rows) for i in range(len(rows[0]))]
            accessor["max"] = [max(row[i] for row in rows) for i in range(len(rows[0]))]
        index = len(self.document["accessors"])
        self.document["accessors"].append(accessor)
        return index

    def finish(self):
        for name in ("textures", "images", "samplers"):
            if not self.document[name]:
                del self.document[name]
        self.document["buffers"] = [{"byteLength": len(self.binary)}]
        data = json.dumps(self.document, separators=(",", ":"), allow_nan=False).encode("utf-8")
        data += b" " * (-len(data) % 4)
        self.binary.extend(b"\0" * (-len(self.binary) % 4))
        length = 12 + 8 + len(data) + 8 + len(self.binary)
        return (struct.pack("<III", 0x46546c67, 2, length) + struct.pack("<II", len(data), 0x4e4f534a) + data +
                struct.pack("<II", len(self.binary), 0x004e4942) + self.binary)


def column_major(matrix):
    return [matrix[row * 4 + col] for col in range(4) for row in range(4)]


def unit_quaternion(q):
    length = math.sqrt(sum(v * v for v in q))
    if length < 0.5:
        raise ValueError("Animation produced a degenerate quaternion")
    return [v / length for v in q]


def append_animation(glb, rig, clip):
    if clip["bone_count"] != rig["bone_count"] or clip["inspected_upstream_commit"] != rig["inspected_upstream_commit"]:
        raise ValueError("Animation must match the supplied skeleton's bone count and inspected profile")
    # LINEAR rotation channels in glTF use spherical interpolation. THUG's
    # FastSlerp is normalized linear interpolation, so bake authentic samples
    # with STEP interpolation instead of silently changing the source curve.
    duration = clip["duration_seconds"]
    times = [f32(index / 60) for index in range(math.ceil(duration * 60)) if f32(index / 60) < duration]
    times.append(duration)
    if len(times) * clip["bone_count"] > MAX_BAKED_POSES:
        raise ValueError("Animation preview exceeds the supported baked pose limit")
    input_index = glb.attribute([[v] for v in times], "f", 5126, "SCALAR", True)
    animation = {"name": "THUG local clip", "samplers": [], "channels": [],
                 "extras": {"source_sha256": clip["source_sha256"], "sample_rate": 60,
                            "pose_semantics": clip["pose_semantics"], "root_motion_preserved": True,
                            "preview_interpolation": "STEP", "fractional_time_preview": "holds preceding 60 Hz sample"}}
    adjustment = 0.0
    compressed = bool(clip["source_flags"] & COMPRESS_TABLE)
    for index, (bone, track) in enumerate(zip(rig["bones"], clip["tracks"])):
        node = glb.document["nodes"][index + 1]
        del node["matrix"]
        q = bone["source_quaternion_xyzw"]
        node["rotation"] = unit_quaternion([-q[0], -q[1], -q[2], q[3]])
        node["translation"] = [v * 0.0254 for v in bone["source_translation_xyzw_inches"][:3]]
        rotations, translations = [], []
        for time in times:
            q, t = sample_track(track, time, compressed)
            normalized = unit_quaternion(q)
            adjustment = max(adjustment, *(abs(a - b) for a, b in zip(q, normalized)))
            rotations.append([-normalized[0], -normalized[1], -normalized[2], normalized[3]])
            translations.append([v * 0.0254 for v in t])
        for path, rows, fmt, kind in (("rotation", rotations, "4f", "VEC4"), ("translation", translations, "3f", "VEC3")):
            output = glb.attribute(rows, fmt, 5126, kind)
            animation["channels"].append({"sampler": len(animation["samplers"]), "target": {"node": index + 1, "path": path}})
            animation["samplers"].append({"input": input_index, "output": output, "interpolation": "STEP"})
    glb.document["animations"] = [animation]
    return {"animation_source_format": clip["source_format"], "animation_duration_seconds": duration,
            "animation_sample_count": len(times), "animation_sample_rate": 60,
            "animation_preview_interpolation": "STEP", "maximum_preview_quaternion_adjustment": adjustment,
            "animation_bone_identity_verified": False, "root_motion_preserved": True,
            "animation_gameplay_mapping": False, "custom_animation_events_applied": False}


def append_textures(glb, dictionary):
    result = {}
    for texture in dictionary["textures"]:
        image = png(texture["mips"][0]["rgba"], texture["width"], texture["height"])
        view = glb.blob(image)
        image_index = len(glb.document["images"])
        glb.document["images"].append({"name": "texture_" + texture["source_id"][2:], "mimeType": "image/png", "bufferView": view,
                                       "extras": {"source_id": texture["source_id"], "source_format": texture["format"],
                                                  "source_mip_levels": texture["levels"]}})
        texture_index = len(glb.document["textures"])
        glb.document["textures"].append({"source": image_index})
        result[texture["source_id"]] = texture_index
    return result


def build(rig, mesh, animation=None, texture_dictionary=None):
    if rig["inspected_upstream_commit"] != mesh["inspected_upstream_commit"]:
        raise ValueError("Skeleton and mesh use different inspected source profiles")
    glb = Glb()
    bones = rig["bones"]
    nodes = glb.document["nodes"]
    nodes.append({"name": "GonkSkate local THUG rig", "children": [1]})
    # glTF skinned mesh nodes are scene roots: skeleton matrices supply their
    # placement. A mesh's parent transform would not move its skinned vertices.
    glb.document["scenes"][0]["nodes"] = [0, len(bones) + 1]
    for bone in bones:
        node = {"name": "bone_" + bone["source_id"][2:], "matrix": column_major(bone["rest_local_matrix"]),
                "extras": {"source_id": bone["source_id"], "source_flip_id": bone["source_flip_id"]}}
        children = [b["index"] + 1 for b in bones if b["parent_index"] == bone["index"]]
        if children:
            node["children"] = children
        nodes.append(node)
    nodes.append({"name": "THUG skinned geometry", "mesh": 0, "skin": 0})
    inverse = glb.attribute([column_major(b["inverse_bind_matrix"]) for b in bones], "16f", 5126, "MAT4")
    glb.document["skins"].append({"name": "THUG original rig", "joints": list(range(1, len(bones) + 1)),
                                  "skeleton": 1, "inverseBindMatrices": inverse})
    texture_ids = append_textures(glb, texture_dictionary) if texture_dictionary is not None else {}
    material_ids = {}
    for material in mesh["materials"]:
        if not material["dictionary_effective"]:
            continue
        material_ids[material["source_id"]] = len(glb.document["materials"])
        # A neutral surface makes missing textures explicit. Source descriptors
        # stay in character.json; source shaders/blend modes are not approximated.
        first = material["passes"][0]
        textured = bool(first["flags"] & 4)
        texture_index = texture_ids.get(first["texture_id"])
        if texture_dictionary is not None and textured and texture_index is None:
            raise ValueError("Texture dictionary is missing a material's first-pass texture: " + first["texture_id"])
        pbr = {"baseColorFactor": [1, 1, 1, 1] if texture_index is not None else [0.65, 0.65, 0.65, 1],
               "metallicFactor": 0, "roughnessFactor": 1}
        if texture_index is not None:
            pbr["baseColorTexture"] = {"index": texture_index, "texCoord": 0}
        entry = {"name": ("textured_" if texture_index is not None else "untextured_") + material["source_id"][2:],
                 "doubleSided": not material["single_sided"] or material["no_backface_culling"],
                 "pbrMetallicRoughness": pbr,
                 "extras": {"source_material_id": material["source_id"], "textures_imported": texture_index is not None,
                            "source_texture_id": first["texture_id"], "source_pass_count": len(material["passes"]),
                            "source_render_effects_applied": False,
                            "preview_limitation": "first texture pass only; original blend, wibble, environment and multi-pass effects remain metadata"}}
        if first["flags"] & (1 << 6):
            entry["alphaMode"] = "BLEND"
        glb.document["materials"].append(entry)
    primitives = []
    used_vertices = 0
    triangle_count = 0
    max_weight_adjustment = 0.0
    for sector in mesh["sectors"]:
        if sector["weights"] is None:
            raise ValueError("Unweighted/rigid character parts need their original attachment adapter")
        if sector["bone_index"] != -1:
            raise ValueError("Skinned sector also has a rigid bone attachment; original placement must be resolved")
        for item in sector["meshes"]:
            flat = triangles(item["lod_strips"][0])
            if not flat:
                continue
            material_index = material_ids[item["material_id"]]
            if ("baseColorTexture" in glb.document["materials"][material_index]["pbrMetallicRoughness"] and
                    sector["uv_set_count"] == 0):
                raise ValueError("Textured character primitive has no source UV set")
            used = sorted(set(flat))
            if used_vertices + len(used) > MAX_VERTICES:
                raise ValueError("Exported character vertex limit exceeded")
            mapping = {value: index for index, value in enumerate(used)}
            positions = [[v * 0.0254 for v in sector["positions_inches"][i]] for i in used]
            normals = []
            weights = []
            joints = []
            for index in used:
                normal = sector["normals"][index]
                length = math.sqrt(sum(v * v for v in normal))
                if not 0.5 <= length <= 1.5:
                    raise ValueError("Unsupported character normal magnitude")
                normals.append([v / length for v in normal])
                source_weights = sector["weights"][index]
                source_joints = sector["joints"][index]
                if any(joint >= len(bones) for joint, weight in zip(source_joints, source_weights) if weight > 0):
                    raise ValueError("Mesh influences reference bones missing from the supplied skeleton")
                total = sum(source_weights)
                normalized = [v / total for v in source_weights]
                max_weight_adjustment = max(max_weight_adjustment, *(abs(a - b) for a, b in zip(source_weights, normalized)))
                weights.append(normalized)
                # Unused source slots can contain sentinel IDs. Keep them raw
                # in the JSON, but never emit invalid GLTF joint indices.
                joints.append([joint if weight > 0 else 0 for joint, weight in zip(source_joints, source_weights)])
            attributes = {"POSITION": glb.attribute(positions, "3f", 5126, "VEC3", True, 34962),
                          "NORMAL": glb.attribute(normals, "3f", 5126, "VEC3", target=34962),
                          "JOINTS_0": glb.attribute(joints, "4H", 5123, "VEC4", target=34962),
                          "WEIGHTS_0": glb.attribute(weights, "4f", 5126, "VEC4", target=34962)}
            for uv_set in range(sector["uv_set_count"]):
                uv_rows = [sector["uvs"][i][2 * uv_set:2 * uv_set + 2] for i in used]
                attributes[f"TEXCOORD_{uv_set}"] = glb.attribute(uv_rows, "2f", 5126, "VEC2", target=34962)
            if sector["colors_argb"] is not None:
                colors = [sector["colors_argb"][i] for i in used]
                # D3DCOLOR: ARGB numeric value, not a guessed byte-array order.
                rgba = [[((v >> shift) & 255) / 255 for shift in (16, 8, 0, 24)] for v in colors]
                attributes["COLOR_0"] = glb.attribute(rgba, "4f", 5126, "VEC4", target=34962)
            indices = glb.attribute([[mapping[v]] for v in flat], "H", 5123, "SCALAR", target=34963)
            primitives.append({"attributes": attributes, "indices": indices, "mode": 4,
                "material": material_index, "extras": {"source_sector_id": sector["source_id"],
                "source_mesh_index": item["index"], "source_flags": item["source_flags"],
                "source_lod_index_counts": [len(lod) for lod in item["lod_strips"]]}})
            used_vertices += len(used)
            triangle_count += len(flat) // 3
    if not primitives:
        raise ValueError("Character has no nondegenerate weighted triangles")
    glb.document["meshes"].append({"name": "THUG character highest detail", "primitives": primitives})
    summary = {"bone_count": len(bones), "source_vertex_count": mesh["source_vertex_count"],
               "exported_vertex_count": used_vertices, "primitive_count": len(primitives), "triangle_count": triangle_count,
               "weight_profile": mesh["weight_profile"], "maximum_preview_weight_adjustment": max_weight_adjustment,
               "preview_weights_normalized": True, "preview_normals_normalized": True,
               "source_axes_preserved": True, "geometry_imported": True, "skin_weights_imported": True,
               "source_pair_identity_verified": False, "textures_imported": texture_dictionary is not None,
               "texture_count": len(texture_dictionary["textures"]) if texture_dictionary is not None else 0,
               "texture_material_passes_applied": "first-pass-only" if texture_dictionary is not None else "none",
               "source_render_effects_applied": False, "animations_imported": False,
               "retail_validated": False, "playable_character_registered": False}
    if animation is not None:
        summary.update(append_animation(glb, rig, animation))
        summary["animations_imported"] = True
    glb.document["extras"] = {"gonkskate": summary}
    return glb.finish(), summary


def import_files(skeleton, skin, output, weight_profile, animation=None, q_table=None, t_table=None, textures=None):
    skeleton, skin, output = Path(skeleton), Path(skin), Path(output)
    if skeleton.stat().st_size > 12 + 44 * MAX_BONES:
        raise ValueError("Skeleton exceeds the supported SKE v2 profile")
    if skin.stat().st_size > MAX_BYTES:
        raise ValueError("Skin exceeds the supported size limit")
    rig = parse_rig(skeleton.read_bytes())
    mesh = parse_skin(skin.read_bytes(), weight_profile)
    if animation is None and (q_table is not None or t_table is not None):
        raise ValueError("Compression tables require --animation")
    clip = read_clip(animation, q_table, t_table) if animation is not None else None
    texture_dictionary = None
    if textures is not None:
        textures = Path(textures)
        if textures.stat().st_size > MAX_TEXTURE_BYTES:
            raise ValueError("Texture dictionary exceeds the supported size limit")
        texture_dictionary = parse_textures(textures.read_bytes())
    glb, summary = build(rig, mesh, clip, texture_dictionary)
    # Reserve the output directory before writing. Never replace an old import
    # or use a shared temporary directory containing someone else's files.
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    try:
        (output / "character.glb").write_bytes(glb)
        package = {"schema_version": 1, "kind": "gonkskate-character-package", "importer_version": 1,
                   "preview_file": "character.glb", "preview_sha256": hashlib.sha256(glb).hexdigest(),
                   "summary": summary, "rig": rig, "mesh": mesh}
        if clip is not None:
            package["animation"] = clip
        if texture_dictionary is not None:
            package["textures"] = texture_metadata(texture_dictionary)
        (output / "character.json").write_text(json.dumps(package, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(output)
        raise
    return package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skeleton", type=Path)
    parser.add_argument("skin", type=Path)
    parser.add_argument("--weight-profile", choices=WEIGHT_PROFILES, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New local character directory")
    parser.add_argument("--animation", type=Path, help="Optional matching original full skeletal clip")
    parser.add_argument("--q-table", type=Path, help="Local Q48 table if required by the clip")
    parser.add_argument("--t-table", type=Path, help="Local T48 table if required by the clip")
    parser.add_argument("--textures", type=Path, help="Optional matching original texture dictionary")
    args = parser.parse_args()
    try:
        package = import_files(args.skeleton, args.skin, args.output, args.weight_profile, args.animation, args.q_table, args.t_table, args.textures)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Character import failed: {error}\n")
    print(json.dumps(package["summary"], indent=2))
    print("Local rigged preview:", args.output / "character.glb")
    print(("Textured" if args.textures else "Untextured") + " rigged preview" +
          (" with a 60 Hz original clip." if args.animation else " in the neutral pose."))
    print("Playable character attachment and gameplay animation selection remain pending.")


if __name__ == "__main__":
    main()
