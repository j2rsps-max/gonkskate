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


class Glb:
    def __init__(self):
        self.binary = bytearray()
        self.document = {"asset": {"version": "2.0", "generator": "GonkSkate THUG character importer v1"},
                         "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [], "meshes": [],
                         "skins": [], "materials": [], "bufferViews": [], "accessors": []}

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
        self.document["buffers"] = [{"byteLength": len(self.binary)}]
        data = json.dumps(self.document, separators=(",", ":"), allow_nan=False).encode("utf-8")
        data += b" " * (-len(data) % 4)
        self.binary.extend(b"\0" * (-len(self.binary) % 4))
        length = 12 + 8 + len(data) + 8 + len(self.binary)
        return (struct.pack("<III", 0x46546c67, 2, length) + struct.pack("<II", len(data), 0x4e4f534a) + data +
                struct.pack("<II", len(self.binary), 0x004e4942) + self.binary)


def column_major(matrix):
    return [matrix[row * 4 + col] for col in range(4) for row in range(4)]


def build(rig, mesh):
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
    material_ids = {}
    for material in mesh["materials"]:
        if not material["dictionary_effective"]:
            continue
        material_ids[material["source_id"]] = len(glb.document["materials"])
        # A neutral surface makes missing textures explicit. Source descriptors
        # stay in character.json; source shaders/blend modes are not approximated.
        glb.document["materials"].append({"name": "untextured_" + material["source_id"][2:], "doubleSided": True,
            "pbrMetallicRoughness": {"baseColorFactor": [0.65, 0.65, 0.65, 1], "metallicFactor": 0, "roughnessFactor": 1},
            "extras": {"source_material_id": material["source_id"], "textures_imported": False,
                       "source_render_effects_applied": False}})
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
                "material": material_ids[item["material_id"]], "extras": {"source_sector_id": sector["source_id"],
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
               "source_pair_identity_verified": False, "textures_imported": False, "animations_imported": False,
               "retail_validated": False, "playable_character_registered": False}
    glb.document["extras"] = {"gonkskate": summary}
    return glb.finish(), summary


def import_files(skeleton, skin, output, weight_profile):
    skeleton, skin, output = Path(skeleton), Path(skin), Path(output)
    if skeleton.stat().st_size > 12 + 44 * MAX_BONES:
        raise ValueError("Skeleton exceeds the supported SKE v2 profile")
    if skin.stat().st_size > MAX_BYTES:
        raise ValueError("Skin exceeds the supported size limit")
    rig = parse_rig(skeleton.read_bytes())
    mesh = parse_skin(skin.read_bytes(), weight_profile)
    glb, summary = build(rig, mesh)
    # Reserve the output directory before writing. Never replace an old import
    # or use a shared temporary directory containing someone else's files.
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    try:
        (output / "character.glb").write_bytes(glb)
        package = {"schema_version": 1, "kind": "gonkskate-character-package", "importer_version": 1,
                   "preview_file": "character.glb", "preview_sha256": hashlib.sha256(glb).hexdigest(),
                   "summary": summary, "rig": rig, "mesh": mesh}
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
    args = parser.parse_args()
    try:
        package = import_files(args.skeleton, args.skin, args.output, args.weight_profile)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Character import failed: {error}\n")
    print(json.dumps(package["summary"], indent=2))
    print("Local rigged preview:", args.output / "character.glb")
    print("Untextured neutral pose; animation and playable character attachment remain pending.")


if __name__ == "__main__":
    main()
