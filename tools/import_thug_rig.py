"""Import THUG v2 little-endian SKE hierarchy/rest pose; meshes remain separate.

Layout and matrix semantics follow kisak-thug CSkeletonData::Load and
Mth::QuatVecToMatrix. Retail validation and other game/platform formats remain
pending. Derived rig data stays local and is never included in release assets.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

THUG_PIN="98b4e24921446ccd4b157453e25697f9574f0053"
MAX_BONES=63  # CSkeletonData::Load asserts m_numBones < vMAX_BONES (64).


def f32(value):
    return struct.unpack("<f",struct.pack("<f",value))[0]


def dot(a,b):
    # Preserve the source's float operations and left-to-right accumulation.
    products=[f32(x*y) for x,y in zip(a,b)]
    total=products[0]
    for value in products[1:]:total=f32(total+value)
    return total


def multiply(a,b):
    return [[dot(a[r],[b[k][c] for k in range(4)]) for c in range(4)] for r in range(4)]


def inverse_uniform(matrix):
    # Source Mth::Matrix::InvertUniform: inverse of its orthonormal row-vector
    # transform, preserving the source convention rather than inventing a rig.
    result=[[matrix[c][r] for c in range(3)]+[0.0] for r in range(3)]
    result.append([-dot(matrix[3][:3],matrix[r][:3]) for r in range(3)]+[1.0])
    return result


def quat_vector(q,t):
    # QuatVecToMatrix conjugates the quaternion via Vector::Negate (XYZ only).
    x,y,z,w=-q[0],-q[1],-q[2],q[3]
    xx,yy,zz=f32(x*x),f32(y*y),f32(z*z)
    yz,zx,xy=f32(y*z),f32(z*x),f32(x*y)
    wx,wy,wz=f32(w*x),f32(w*y),f32(w*z)
    def diagonal(a,b):return f32(1-f32(2*f32(a+b)))
    def off(a,b):return f32(2*f32(a+b))
    return [[diagonal(yy,zz),off(xy,wz),off(zx,-wy),0.0],
            [off(xy,-wz),diagonal(xx,zz),off(yz,wx),0.0],
            [off(zx,wy),off(yz,-wx),diagonal(xx,yy),0.0],
            [t[0],t[1],t[2],1.0]]


def normalized_matrix(source):
    # Convert row-vector THUG matrices into row-major arrays for column vectors;
    # translations become meters. No additional axis/rig rotation is assumed.
    matrix=[[source[c][r] for c in range(4)] for r in range(4)]
    for row in range(3):matrix[row][3]*=0.0254
    return [value for row in matrix for value in row]


def parse(data):
    if len(data)<12:raise ValueError("Truncated SKE header")
    version,flags,count=struct.unpack_from("<III",data)
    if version!=2:raise ValueError("Supported profile is SKE v2 little-endian; other versions/platforms need verification")
    if not 1<=count<=MAX_BONES:raise ValueError("Bone count exceeds the inspected THUG loader's bounds")
    if len(data)!=12+44*count:raise ValueError("SKE size does not match hierarchy/rest-pose counts")
    names=list(struct.unpack_from(f"<{count}I",data,12))
    parents=list(struct.unpack_from(f"<{count}I",data,12+4*count))
    flips=list(struct.unpack_from(f"<{count}I",data,12+8*count))
    if len(set(names))!=count:raise ValueError("Duplicate bone identifiers")
    indexes={name:index for index,name in enumerate(names)}
    if parents[0] not in (0,names[0]):raise ValueError("Root parent must be zero or itself")
    inverses=[];bones=[]
    for index in range(count):
        if index:
            parent=indexes.get(parents[index])
            if parent is None or parent>=index:raise ValueError("Parents must exist before their children, as required by the source neutral-pose loader")
        else:parent=None
        if flips[index] and flips[index] not in indexes:raise ValueError("Unknown flipped-bone identifier")
        values=struct.unpack_from("<8f",data,12+12*count+32*index)
        if any(not math.isfinite(v) for v in values):raise ValueError("Non-finite rest pose")
        q,t=list(values[:4]),list(values[4:])
        if abs(sum(v*v for v in q)-1)>1e-3:raise ValueError("Rest quaternion is not normalized; source uniform inversion would be invalid")
        if any(abs(v)>1000000 for v in t):raise ValueError("Rest translation outside supported bounds")
        local=quat_vector(q,t)
        world=multiply(local,inverse_uniform(inverses[parent])) if parent is not None else local
        for row in range(3):world[row][3]=0.0
        world[3][3]=1.0
        inverse=inverse_uniform(world);inverses.append(inverse)
        bones.append({"index":index,"source_id":f"0x{names[index]:08x}","parent_index":parent,
                      "source_parent_id":f"0x{parents[index]:08x}","source_flip_id":f"0x{flips[index]:08x}",
                      "flip_index":indexes[flips[index]] if flips[index] else None,
                      "source_quaternion_xyzw":q,"source_translation_xyzw_inches":t,
                      "rest_local_matrix":normalized_matrix(local),"rest_world_matrix":normalized_matrix(world),
                      "inverse_bind_matrix":normalized_matrix(inverse)})
    return {"schema_version":1,"kind":"gonkskate-character-rig","source_game":"thug",
            "source_format":"ske-v2-little-endian","source_sha256":hashlib.sha256(data).hexdigest(),
            "inspected_upstream_commit":THUG_PIN,"source_flags":flags,"units":"meter",
            "matrix_layout":"row-major, column-vector affine","bone_count":count,"bones":bones,
            "source_math":"THUG scalar float32 quaternion/matrix operations",
            "mesh_imported":False,"animations_imported":False,"retail_validated":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skeleton",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.skeleton.stat().st_size>12+44*MAX_BONES:raise ValueError("File exceeds this verified SKE profile's maximum size")
        rig=parse(args.skeleton.read_bytes())
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open("x",encoding="utf-8") as output:
            json.dump(rig,output,indent=2,allow_nan=False);output.write("\n")
    except (ValueError,OSError) as error:parser.exit(1,f"Rig import failed: {error}\n")
    print(f"Imported {rig['bone_count']} bones and neutral pose: {args.output}")
    print("Rig only; character mesh, materials, animations and retail validation remain pending.")


if __name__=="__main__":main()
