"""Compare rig import with the original THUG skeleton loader and math code.

Synthetic valid fixtures only. Extracted upstream methods remain in build/;
this is source differential validation, not retail character compatibility.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import subprocess
from import_thug_rig import THUG_PIN, normalized_matrix, parse

ROOT=Path(__file__).resolve().parents[1]


def extract(text,marker):
    if text.count(marker)!=1:raise ValueError("Expected one original method: "+marker)
    start=text.index(marker);opening=text.index("{",start);end=opening+1;depth=1
    while depth:
        depth+=(text[end]=="{")-(text[end]=="}");end+=1
    return text[start:end]+"\n"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx",default="/workspace/tooling/llvm/usr/bin/clang++-19")
    args=parser.parse_args()
    upstream=ROOT/"external/kisak-thug"
    pin=subprocess.check_output(["git","-C",str(upstream),"rev-parse","HEAD"],text=True).strip()
    if pin!=THUG_PIN:parser.error("Upstream differs from inspected THUG pin")
    build=ROOT/"build/rig-differential";build.mkdir(parents=True,exist_ok=True)
    code=build/"code"
    subprocess.run(["python3",str(ROOT/"tools/prepare_thug_headless.py"),str(upstream),str(code)],check=True)
    source=(upstream/"Code/Gfx/Skeleton.cpp").read_text()
    methods=["CSkeletonData::CSkeletonData()","CSkeletonData::~CSkeletonData()",
        "bool CSkeletonData::Load( uint32*", "int CSkeletonData::GetNumBones() const",
        "uint32 CSkeletonData::GetBoneName( int", "uint32 CSkeletonData::GetParentName( int",
        "uint32 CSkeletonData::GetIndex( uint32", "Mth::Matrix* CSkeletonData::GetInverseNeutralPoseMatrices()"]
    (build/"upstream_skeleton_data.inc").write_text("\n".join(extract(source,m) for m in methods))
    env=os.environ.copy();env["LD_LIBRARY_PATH"]="/workspace/tooling/llvm/usr/lib/x86_64-linux-gnu"
    flags=["-std=c++17","-fms-extensions","-fdelayed-template-parsing","-D__PLAT_GONK__",
        "-ffunction-sections","-fdata-sections","-Wno-register","-Wno-writable-strings","-Wno-comment",
        "-I"+str(code),"-I"+str(build)]
    objects=[]
    for unit in [ROOT/"native/thug_adapter/tests/upstream_rig_fixture.cpp",code/"core/math/vector.cpp",code/"core/math/matrix.cpp"]:
        obj=build/(unit.stem+".o");objects.append(obj)
        subprocess.run([args.cxx,*flags,"-c",str(unit),"-o",str(obj)],env=env,check=True)
    exe=build/"rig-fixture"
    subprocess.run([args.cxx,*map(str,objects),"-Wl,--gc-sections","-o",str(exe)],env=env,check=True)
    rng=random.Random(0x534b45);max_error=0.0;bone_total=0
    for case in range(40):
        count=[1,3,16,63][case%4];names=list(range(100,100+count))
        parents=[0]+[names[rng.randrange(i)] for i in range(1,count)]
        poses=[]
        for index in range(count):
            axis=[rng.uniform(-1,1) for _ in range(3)];length=math.sqrt(sum(x*x for x in axis))
            angle=rng.uniform(-math.pi,math.pi)/2
            q=[x/length*math.sin(angle) for x in axis]+[math.cos(angle)]
            poses.append(q+[rng.uniform(-100,100) for _ in range(3)]+[rng.choice([0,1])])
        data=struct.pack("<III",2,case,count)+struct.pack(f"<{3*count}I",*names,*parents,*([0]*count))+b"".join(struct.pack("<8f",*p) for p in poses)
        path=build/"synthetic.ske";path.write_bytes(data);rig=parse(data)
        lines=subprocess.check_output([str(exe),str(path)],env=env,text=True).splitlines()
        assert len(lines)==count
        for bone,line in zip(rig["bones"],lines):
            fields=line.split(",");assert int(fields[0])==int(bone["source_id"],16)
            raw=[list(map(float,fields[1+4*r:5+4*r])) for r in range(4)]
            expected=normalized_matrix(raw)
            error=max(abs(a-b) for a,b in zip(expected,bone["inverse_bind_matrix"]))
            max_error=max(max_error,error)
            assert error<1e-5,(case,bone["index"],error)
        bone_total+=count
    report={"upstream_commit":pin,"loader_sha256":hashlib.sha256(source.encode()).hexdigest(),
        "fixtures":40,"bones_compared":bone_total,"maximum_normalized_matrix_error":max_error,
        "inverse_bind_equivalence":"PASS","retail_character_validated":False}
    (build/"validation.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))


if __name__=="__main__":main()
