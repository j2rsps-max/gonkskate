"""Import static visible geometry from pinned Skate3Recomp scene recordings.

Consumes .scene.jsonl, .buffers.bin and .gsnap locally. Static scenery normally
requires the Windows memory snapshot; no ISO is read by this importer.
These are render triangles, not the game's original collision or rail data.
"""
import argparse, collections, contextlib, hashlib, json, math, struct
from pathlib import Path
from gonk_world import validate, MAX_TRIANGLES
from skate3_snapshot import Snapshot, fingerprint

def buffers(path):
    result = collections.defaultdict(list)
    with Path(path).open('rb') as source:
        if source.read(8) != b'SK3BUFS1': raise ValueError('Unsupported Skate buffer capture header')
        size = Path(path).stat().st_size
        if size > 600*1024*1024: raise ValueError('Buffer recording exceeds supported 600 MiB')
        while source.tell() < size:
            header = source.read(24)
            if len(header) != 24: raise ValueError('Truncated buffer header')
            vb, ib, fp, nv, ni = struct.unpack('<IIQII', header)
            if nv > 16*1024*1024 or ni > 16*1024*1024 or nv+ni > size-source.tell():
                raise ValueError('Invalid recorded buffer lengths')
            # Offsets keep memory bounded: only the selected meshes are read.
            result[(vb,ib,fp)].append((source.tell(),nv,ni))
            source.seek(nv+ni,1)
    return result

def cross(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]

def ground(triangles, point):
    best = None
    for a,b,c in triangles:
        # Barycentric projection in X/Z; ignore walls and near-vertical faces.
        n=cross(a,b,c)
        length=math.sqrt(sum(v*v for v in n))
        if not length or abs(n[1])/length < 0.5: continue
        x,z=point[0],point[2]
        det=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
        if abs(det)<1e-12: continue
        u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/det
        v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/det
        if min(u,v,1-u-v)<-1e-6: continue
        y=u*a[1]+v*b[1]+(1-u-v)*c[1]
        if y <= point[1]+0.05 and (best is None or y>best[0]): best=(y,n[1])
    if best is None: raise ValueError('No supporting surface below the camera/spawn; choose --spawn X Y Z in source meters')
    return best

def import_scene(scene_path, buffer_path, frame=-1, radius=25.0, spawn=None, memory_path=None):
    if not math.isfinite(radius) or not 0<radius<=200: raise ValueError('Radius must be 0..200 meters')
    selected = None
    with Path(scene_path).open(encoding='utf-8') as source:
        for index,line in enumerate(source):
            if len(line)>64*1024*1024: raise ValueError('Scene frame exceeds 64 MiB')
            if frame==-1: selected=json.loads(line)
            elif index==frame: selected=json.loads(line);break
    if selected is None: raise ValueError('Capture frame not found')
    center=list(spawn if spawn is not None else selected['cam'])
    if len(center)!=3 or not all(math.isfinite(v) for v in center): raise ValueError('Invalid capture camera/spawn')
    table=buffers(buffer_path);triangles=[];skipped=collections.Counter();seen=set()
    with contextlib.ExitStack() as stack:
        source=stack.enter_context(Path(buffer_path).open('rb'))
        snapshot=stack.enter_context(Snapshot(memory_path)) if memory_path else None
        for item in selected['items']:
            if any(item.get(k,0) for k in ['skinned','pending','decal','transparent','caster','dbg_src']):
                skipped['non_static_or_overlay']+=1;continue
            fmt=item['pos_fmt']
            if fmt not in (57,32): skipped['unsupported_position_format']+=1;continue
            key=tuple(int(item[k],16) for k in ['vb_addr','ib_addr','fp'])
            match=table.get(key,[])
            nv,ni=item['vb_bytes'],item['ib_count']*2
            if type(nv) is not int or type(ni) is not int or not 0<nv<=16*1024*1024 or not 0<ni<=16*1024*1024:
                raise ValueError('Invalid mesh buffer lengths')
            if len(match)==1:
                offset,recorded_v,recorded_i=match[0]
                if nv!=recorded_v or ni!=recorded_i: raise ValueError('Recorded mesh/buffer length mismatch')
                source.seek(offset);vb=source.read(nv);ib=source.read(ni)
            elif not match and snapshot:
                try:
                    vb=snapshot.read_guest(key[0],nv);ib=snapshot.read_guest(key[1],ni)
                except ValueError:
                    skipped['missing_snapshot_region']+=1;continue
                if fingerprint(key[0],key[1],vb,ib)!=key[2]:
                    skipped['snapshot_fingerprint_mismatch']+=1;continue
            else:
                skipped['missing_or_ambiguous_buffer']+=1;continue
            stride,position=item['stride'],item['pos_off'];width=12 if fmt==57 else 8
            if stride<=0 or position<0 or position+width>stride or nv%stride: raise ValueError('Invalid vertex layout')
            m=item['world']
            if len(m)!=16 or not all(math.isfinite(x) for x in m): raise ValueError('Invalid world transform')
            if max(abs(m[i]) for i in [3,7,11])+abs(m[15]-1)>1e-4: raise ValueError('Non-affine world matrix')
            if len(vb)!=nv or len(ib)!=ni: raise ValueError('Truncated mesh payload')
            points=[]
            for i in range(nv//stride):
                xyz=struct.unpack_from('>3f' if fmt==57 else '>3e',vb,i*stride+position)
                point=[sum(xyz[k]*m[k*4+j] for k in range(3))+m[12+j] for j in range(3)]
                if not all(math.isfinite(x) and abs(x)<250000 for x in point): raise ValueError('Invalid decoded position')
                points.append(point)
            indices=struct.unpack('>'+str(ni//2)+'H',ib)
            for prim,base,start,count in item['draws']:
                if any(type(v) is not int or not 0<=v<=0xFFFFFFFF for v in [prim,base,start,count]):
                    raise ValueError('Invalid draw arguments')
                if prim not in (4,6): skipped['unsupported_primitive']+=1;continue
                if base>=0x80000000: base-=0x100000000  # Guest signed BaseVertexIndex.
                if start+count>len(indices): raise ValueError('Invalid draw index range')
                strip=[]
                if prim==4:
                    if count%3: raise ValueError('Triangle list count is not divisible by three')
                    faces=[indices[i:i+3] for i in range(start,start+count,3)]
                else:
                    faces=[]
                    for value in indices[start:start+count]:
                        if value==65535: strip=[];continue
                        strip.append(value)
                        if len(strip)>=3:
                            face=strip[-3:];faces.append(face if len(strip)%2 else [face[1],face[0],face[2]])
                for face in faces:
                    ix=[base+i for i in face]
                    if min(ix,default=0)<0 or max(ix,default=-1)>=len(points): raise ValueError('Vertex index outside buffer')
                    if len(set(ix))!=3: continue
                    vertices=[points[i] for i in ix]
                    if any(min(v[k] for v in vertices)>center[k]+radius or max(v[k] for v in vertices)<center[k]-radius for k in [0,2]): continue
                    if sum(x*x for x in cross(*vertices))<1e-16: continue
                    signature=tuple(sorted(tuple(v) for v in vertices))
                    if signature in seen: continue
                    seen.add(signature);triangles.append(vertices)
                    if len(triangles)>MAX_TRIANGLES: raise ValueError('Too many triangles; reduce --radius')
    try: support,ny=ground(triangles,center)
    except ValueError as error: raise ValueError(f'{error}; skipped meshes: {dict(skipped)}') from error
    # Rebase near the chosen support surface; keep renderer and native simulation
    # on precisely the same float32 inch coordinates. Infer ONE global winding
    # convention from the support face, preserving wall/ceiling orientation.
    origin=[center[0],support,center[2]];flip=ny<0;normalized=[]
    for vertices in triangles:
        vertices=[[(v[i]-origin[i])/0.0254 for i in range(3)] for v in vertices]
        if flip: vertices[1],vertices[2]=vertices[2],vertices[1]
        normalized.append({'vertices':vertices,'flags':1,'terrain':1})
    world=validate({'schema_version':1,'units':'inch','name':'Skate 3 captured area','source_game':'skate3-render-capture',
                    'floor':False,'spawn':[0,0,0],'triangles':normalized,'rails':[],
                    'provenance':{'importer':'skate3-scene-v2','frame':frame,'generation':selected['generation'],
                                  'source_origin_meters':origin,'radius_meters':radius,'flipped_winding':flip,
                                  'collision':'visible render geometry; generic concrete; original collision/rails not captured',
                                  'skipped':dict(skipped),'scene_sha256':hashlib.sha256(Path(scene_path).read_bytes()).hexdigest(),
                                  'buffers_sha256':file_hash(buffer_path),
                                  'snapshot_sha256':file_hash(memory_path) if memory_path else None}})
    return world

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('scene',type=Path);p.add_argument('--buffers',type=Path);p.add_argument('--memory',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--frame',type=int,default=-1,help='Zero-based frame; -1 selects last (closest to snapshot)')
    p.add_argument('--radius',type=float,default=25);p.add_argument('--spawn',type=float,nargs=3)
    a=p.parse_args()
    if a.frame < -1:p.error('Frame must be -1 or nonnegative')
    if a.output.exists():p.error('Output exists; choose a new world file')
    binary=a.buffers or a.scene.with_name(a.scene.name.removesuffix('.scene.jsonl')+'.buffers.bin')
    memory=a.memory or a.scene.with_name(a.scene.name.removesuffix('.scene.jsonl')+'.gsnap')
    world=import_scene(a.scene,binary,a.frame,a.radius,a.spawn,memory if memory.exists() else None)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(world,separators=(',',':'))+'\n')
    print(f"Imported {len(world['triangles'])} Skate render triangles: {a.output}")
    print('Skipped:',world['provenance']['skipped'])
