"""Compare skin import with original THUG material/sector readers on Windows.

Exact original read bodies execute under the Windows data model (including
32-bit unsigned long) with allocation/render capture facades. Synthetic files
only. This verifies streams, not original D3D rendering or retail appearance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from import_thug_rig import THUG_PIN
from import_thug_skin import parse, triangles
from test_thug_character import material_fixture, sector_fixture, skin_fixture
from test_thug_rig_upstream import extract

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default="/workspace/tooling/llvm/usr/bin/clang++-19")
    parser.add_argument("--runner", nargs="+", default=[])
    args = parser.parse_args()
    if sys.platform != "win32" and not args.runner:
        parser.error("This differential fixture needs Windows or --runner wine64")
    upstream = ROOT / "external/kisak-thug"
    pin = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    if pin != THUG_PIN:
        parser.error("Upstream differs from the inspected pin")
    build = ROOT / "build/skin-differential"
    build.mkdir(parents=True, exist_ok=True)
    sector = (upstream / "Code/Gfx/XBox/p_nxsector.cpp").read_text()
    material = (upstream / "Code/Gfx/XBox/NX/material.cpp").read_text()
    flags = (upstream / "Code/Gfx/XBox/NX/material.h").read_text()
    instance = (upstream / "Code/Gfx/XBox/NX/instance.cpp").read_text()
    dx9 = (upstream / "Code/Gfx/DX9/NX/mesh.cpp").read_text()
    methods = {"upstream_sector_loader.inc": extract(sector, "bool CXboxSector::LoadFromMemory"),
               "upstream_material_loader.inc": extract(material, "Lst::HashTable< sMaterial >\t*LoadMaterialsFromMemory")}
    for name, text in methods.items():
        (build / name).write_text(text)
    (build / "upstream_material_flags.inc").write_text("\n".join(line for line in flags.splitlines() if line.startswith("#define MATFLAG_")) + "\n")
    xbox_decode = "\n".join(line.strip() for line in instance.splitlines() if re.match(r"\s*float\s+w[012]\s*=", line))
    if len(xbox_decode.splitlines()) != 3:
        raise ValueError("Original Xbox weight decode changed")
    start = dx9.index("uint32 read0 = p_weights_read[0];")
    end = dx9.index("p_weights_write[2] = (float)readbits / 512.0f;", start) + len("p_weights_write[2] = (float)readbits / 512.0f;")
    (build / "upstream_weight_decode.inc").write_text("""
void original_xbox(uint32 packed_weights,float* out){
""" + xbox_decode + "\nout[0]=w0;out[1]=w1;out[2]=w2;}\n" + """
void original_dx9(uint32 packed,float* p_weights_write){uint32* p_weights_read=&packed;
""" + dx9[start:end] + "\n}\n")
    original_strip = extract(dx9, "for (int i = 0; i < this->m_num_indices[0] - 2; i++)")
    (build / "upstream_strip.inc").write_text(original_strip)
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = "/workspace/tooling/llvm/usr/lib/x86_64-linux-gnu"
    mingw = Path(os.environ.get("GONK_MINGW", "/workspace/tooling/mingw/usr"))
    gcc = mingw / "lib/gcc/x86_64-w64-mingw32/14-posix"
    options = ["-std=c++17", "-I" + str(build), "-static", "-pthread"]
    if sys.platform != "win32":
        options += ["--target=x86_64-w64-windows-gnu", "--sysroot=" + str(mingw / "x86_64-w64-mingw32"),
                    "-I" + str(gcc / "include/c++"), "-I" + str(gcc / "include/c++/x86_64-w64-mingw32"),
                    "-L" + str(gcc), "-B" + str(mingw / "bin")]
    exe = build / "skin-fixture.exe"
    subprocess.run([args.cxx, *options, str(ROOT / "native/thug_adapter/tests/upstream_skin_fixture.cpp"),
                    "-o", str(exe)], env=environment, check=True)
    fixtures = 0
    vertices = 0
    for case in range(26):
        sectors = [sector_fixture(identity=200 + i, flags=flags) for i, flags in
                   enumerate(([0x817, 0x14, 0x17, 0x814] if case % 2 else [0x817]))]
        raw = skin_fixture(effects=bool(case % 3), passes=1 + case % 4, sectors=sectors)
        if case >= 24:
            import struct
            raw = (struct.pack("<4I", 7, 8, 9, 3) + material_fixture(0) + material_fixture(0, effects=True) +
                   material_fixture(100, effects=bool(case % 2)) + struct.pack("<i", len(sectors)) +
                   b"".join(sectors) + struct.pack("<i", 0))
        path = build / "synthetic.skin"
        path.write_bytes(raw)
        mesh = parse(raw, "xbox")
        lines = subprocess.check_output([*args.runner, str(exe), path.name], env=environment, cwd=build,
                                        text=True, timeout=30).splitlines()
        expected = [["materials_end", mesh["materials_end"]]]
        for m in mesh["materials"]:
            if not m["dictionary_effective"]:
                continue
            expected.append(["material", int(m["source_id"], 16), int(m["source_name_id"], 16), len(m["passes"]), m["alpha_cutoff"]])
            neutral = all(p["color"] == [0.5, 0.5, 0.5] for p in m["passes"])
            for index, p in enumerate(m["passes"]):
                source_flags = p["flags"]
                if index == 0:
                    if neutral: source_flags |= 1 << 28
                    if m["specular_power"] > 0: source_flags |= 1 << 8
                alpha = int(p["alpha_register"], 16)
                expected.append(["pass", source_flags, (alpha & 0xffffff) | ((alpha >> 32) << 24), (alpha >> 32) / 128])
        for s in mesh["sectors"]:
            expected.append(["sector_end", s["source_end"], int(s["source_id"], 16), s["source_flags"]])
        def flat(values):
            return [v for row in values for v in row] if values else []
        for s in mesh["sectors"]:
            for item in s["meshes"]:
                expected += [["mesh", s["vertex_count"], s["uv_set_count"], int(item["material_id"], 16)],
                             ["positions", *flat(s["positions_inches"])], ["normals", *flat(s["normals"])],
                             ["uvs", *flat(s["uvs"])], ["colors", *(s["colors_argb"] or [])],
                             ["weights", *s["weights_packed"]], ["joints", *flat(s["joints"])],
                             ["wibble", *(s["vertex_color_wibble_indices"] or [])]]
                expected += [["lod", *lod] for lod in item["lod_strips"]]
                expected += [["triangles", *triangles(item["lod_strips"][0])]]
                for profile in ("xbox", "dx9"):
                    decoded = parse(raw, profile)["sectors"][mesh["sectors"].index(s)]["weights"]
                    expected += [["decode_" + profile, *row[:3]] for row in decoded]
        assert len(lines) == len(expected), (case, len(lines), len(expected))
        for actual, wanted in zip(lines, expected):
            fields = actual.split(",")
            assert fields[0] == wanted[0] and len(fields) == len(wanted), (case, fields, wanted)
            for value, original in zip(fields[1:], wanted[1:]):
                assert abs(float(value) - original) < 1e-7, (case, fields[0], value, original)
        fixtures += 1
        vertices += mesh["source_vertex_count"]
    report = {"passed": True, "upstream_commit": pin, "original_loader_stream_equivalence": "PASS",
              "original_strip_conversion": "PASS", "original_xbox_and_dx9_weight_decode": "PASS",
              "fixtures": fixtures, "vertices_compared": vertices, "execution": "Windows x64" + (" under Wine" if args.runner else ""),
              "source_method_sha256": {name: hashlib.sha256(text.encode()).hexdigest() for name, text in methods.items()},
              "importer_source_sha256": {name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
                  for name in ("import_thug_rig.py", "import_thug_skin.py", "import_thug_character.py")},
              "allocation_and_render_environment": "capture facades; no D3D renderer", "retail_character_validated": False}
    (build / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
