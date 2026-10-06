"""Compare texture layout and exact original unswizzle with synthetic files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess

from import_thug_rig import THUG_PIN
from import_thug_texture import parse, unswizzle
from test_thug_animation_upstream import extract
from test_thug_texture import bc1_block, bc3_block, swizzle, texture_fixture, texture_record

ROOT = Path(__file__).resolve().parents[1]


def fnv(data):
    value = 1469598103934665603
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default="/workspace/tooling/llvm/usr/bin/clang++-19")
    args = parser.parse_args()
    upstream = ROOT / "external/kisak-thug"
    pin = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    if pin != THUG_PIN:
        parser.error("Upstream differs from inspected THUG pin")
    if subprocess.check_output(["git", "-C", str(upstream), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        parser.error("Original source comparison requires an unmodified tracked upstream checkout")
    source = (upstream / "Code/Gfx/DX9/p_nxtexture.cpp").read_text()
    original_reader = extract(source, "static Lst::HashTable<Nx::CTexture>* LoadTextureFile_Internal")
    texture_math = (upstream / "Code/Gfx/DX9/NX/texture.cpp").read_text()
    original_unswizzle = extract(texture_math, "void Unswizzle(")
    build = ROOT / "build/texture-differential"
    build.mkdir(parents=True, exist_ok=True)
    (build / "upstream_unswizzle.inc").write_text(original_unswizzle)
    exe = build / "texture-fixture"
    env = os.environ.copy(); env["LD_LIBRARY_PATH"] = "/workspace/tooling/llvm/usr/lib/x86_64-linux-gnu"
    subprocess.run([args.cxx, "-std=c++17", "-I" + str(build),
        str(ROOT / "native/thug_adapter/tests/upstream_texture_fixture.cpp"), "-o", str(exe)], check=True, env=env)
    rng = random.Random(0x544558)
    count = mips = pixels = 0
    for case in range(24):
        records = []
        for index in range(1 + case % 4):
            width, height = 1 << (2 + (case + index) % 4), 1 << (1 + index % 3)
            levels = 1 + min(case % 3, int(__import__('math').log2(max(width, height))))
            profile = (case + index) % 5
            identity = 1000 + case * 4 + index
            raw_mips = []
            if profile == 0:
                depth, dxt, palette = 32, 0, b""
                for level in range(levels):
                    w, h = max(1,width>>level),max(1,height>>level)
                    linear=bytes(rng.randrange(256) for _ in range(w*h*4));raw_mips.append(swizzle(linear,w,h,4))
            elif profile == 1:
                depth, dxt, palette = 16, 0, b""
                for level in range(levels):
                    w,h=max(1,width>>level),max(1,height>>level)
                    linear=bytes(rng.randrange(256) for _ in range(w*h*2));raw_mips.append(swizzle(linear,w,h,2))
            elif profile == 2:
                depth,dxt=8,0;palette=bytes(rng.randrange(256) for _ in range(1024))
                for level in range(levels):
                    w,h=max(1,width>>level),max(1,height>>level)
                    linear=bytes(rng.randrange(256) for _ in range(w*h));raw_mips.append(swizzle(linear,w,h,1))
            elif profile == 3:
                depth,dxt,palette=4,1,b""
                for level in range(levels):
                    w,h=max(1,width>>level),max(1,height>>level)
                    raw_mips.append(bc1_block(rng.randrange(65536),rng.randrange(65536),rng.randrange(1<<32))* (max(1,(w+3)//4)*max(1,(h+3)//4)))
            else:
                depth,dxt,palette=8,5,b""
                for level in range(levels):
                    w,h=max(1,width>>level),max(1,height>>level)
                    raw_mips.append(bc3_block()* (max(1,(w+3)//4)*max(1,(h+3)//4)))
            records.append(texture_record(identity,width,height,depth,dxt,levels,palette,raw_mips))
        raw = texture_fixture(records, version=case)
        path = build / "synthetic.tex";path.write_bytes(raw)
        parsed = parse(raw)
        lines = subprocess.check_output([str(exe), str(path)], text=True, env=env).splitlines()
        assert lines.pop(0) == f"header,{case},{len(records)}"
        expected=[]
        for texture in parsed["textures"]:
            palette_hash = 1469598103934665603 if not texture["palette_entries"] else None
            # Recover palette hash from the source span preceding its first mip.
            offset=texture["source_offset"]+32
            palette_size=texture["palette_entries"]*4
            if palette_size:palette_hash=fnv(raw[offset:offset+palette_size])
            expected.append(["texture",int(texture["source_id"],16),texture["width"],texture["height"],texture["levels"],
                texture["texel_depth"],texture["palette_depth"],texture["dxt"],palette_size,palette_hash])
            cursor=offset+palette_size
            for mip in texture["mips"]:
                size=struct.unpack_from("<I",raw,cursor)[0];cursor+=4;source=raw[cursor:cursor+size];cursor+=size
                linear=fnv(unswizzle(source,mip["width"],mip["height"],texture["texel_depth"]//8)) if not texture["dxt"] else 0
                expected.append(["mip",texture["index"],mip["level"],size,fnv(source),linear])
                mips+=1;pixels+=mip["width"]*mip["height"]
        for line,wanted in zip(lines,expected):
            fields=line.split(',');assert fields[0]==wanted[0] and list(map(int,fields[1:]))==wanted[1:],(case,fields,wanted)
        assert lines[len(expected)]==f"end,{len(raw)}"
        count+=len(records)
    report={"passed":True,"upstream_commit":pin,"source_layout_method_sha256":hashlib.sha256(original_reader.encode()).hexdigest(),
        "exact_original_unswizzle_sha256":hashlib.sha256(original_unswizzle.encode()).hexdigest(),
        "original_unswizzle_equivalence":"PASS","source_stream_offsets_and_bytes":"PASS","fixtures":24,"textures_compared":count,
        "mips_compared":mips,"pixels_decoded":pixels,"retail_texture_validated":False,
        "importer_source_sha256":{"import_thug_texture.py":hashlib.sha256((ROOT/"tools/import_thug_texture.py").read_bytes()).hexdigest()}}
    (build/"validation.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))


if __name__ == "__main__": main()
