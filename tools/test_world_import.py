"""Independent format fixtures and authentic physics checks for imported worlds."""
import argparse, csv, copy, io, json, math, struct, subprocess, tempfile, unittest
from pathlib import Path
from gonk_world import encode, validate
from import_obj_world import import_obj
from import_skate3_scene import import_scene
from skate3_snapshot import Snapshot, fingerprint

ROOT=Path(__file__).resolve().parents[1]

def capture_fixture(path):
    # Fixture follows upstream WriteRecording()'s documented host LE record
    # headers and raw guest BE vertex/index payloads. No retail assets.
    points=[[-15,0,-10],[-15,0,100],[15,0,-10],[15,0,100]]
    vb=b''.join(struct.pack('>3f',*p) for p in points);ib=struct.pack('>6H',0,1,2,2,1,3)
    buf=path/'fixture.buffers.bin'
    buf.write_bytes(b'SK3BUFS1'+struct.pack('<IIQII',0x1000,0x2000,0x1234,len(vb),len(ib))+vb+ib)
    world=[1,0,0,0,0,1,0,0,0,0,1,0,10,2,20,1]
    item={'mesh':'40','vb_addr':'1000','ib_addr':'2000','fp':'1234','vb_bytes':len(vb),'ib_count':6,
          'stride':12,'pos_fmt':57,'pos_off':0,'skinned':0,'pending':0,'decal':0,'transparent':0,
          'caster':0,'world':world,'draws':[[4,0,0,6]]}
    scene=path/'fixture.scene.jsonl';scene.write_text(json.dumps({'generation':70,'cam':[10,5,20],'items':[item,{**item,'skinned':1}],'dynitems':[item]})+'\n')
    return scene,buf,item

def snapshot_fixture(path):
    scene,buf,item=capture_fixture(path)
    payload=buf.read_bytes();vb=payload[32:32+item['vb_bytes']];ib=payload[32+item['vb_bytes']:]
    item.update(vb_addr='10000',ib_addr='e0002000')
    item['fp']=format(fingerprint(0x10000,0xE0002000,vb,ib),'x')
    # Known answer independently obtained by compiling exact upstream
    # ComputeItemFingerprint (pin f6e0ae8) over these non-retail bytes.
    assert item['fp']=='f07188098a008ab5'
    scene.write_text(json.dumps({'generation':70,'cam':[10,5,20],'items':[item]})+'\n')
    buf.write_bytes(b'SK3BUFS1')  # Static world geometry is absent from buffer recording.
    memory=path/'fixture.gsnap'
    # Split VB across two contiguous regions; IB is in the shifted physical map.
    memory.write_bytes(b'SK3GSNP1'+struct.pack('<QQ',0x10000,16)+vb[:16]+
        struct.pack('<QQ',0x10010,len(vb)-16)+vb[16:]+
        struct.pack('<QQ',0xE0003000,len(ib))+ib+struct.pack('<QQ',0xFFFFFFFFFFFFFFFF,0))
    return scene,buf,memory,item

class ImportTests(unittest.TestCase):
    def test_static_snapshot_fingerprint_regions_and_last_frame(self):
        with tempfile.TemporaryDirectory() as d:
            scene,buf,memory,item=snapshot_fixture(Path(d))
            world=import_scene(scene,buf,memory_path=memory)
            self.assertEqual(len(world['triangles']),2)
            self.assertIsNotNone(world['provenance']['snapshot_sha256'])
            first={'generation':1,'cam':[10,5,20],'items':[]}
            scene.write_text(json.dumps(first)+'\n'+scene.read_text())
            self.assertEqual(import_scene(scene,buf,memory_path=memory)['provenance']['generation'],70)
            item['fp']='1'
            scene.write_text(json.dumps({'generation':1,'cam':[10,5,20],'items':[item]})+'\n')
            with self.assertRaisesRegex(ValueError,'snapshot_fingerprint_mismatch'):
                import_scene(scene,buf,memory_path=memory)
            with Snapshot(memory) as reader:
                with self.assertRaisesRegex(ValueError,'missing'):reader.read_guest(0x20000,8)
                with self.assertRaisesRegex(ValueError,'boundary'):reader.read_guest(0xDFFFFFFF,8)
            memory.write_bytes(memory.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError,'Truncated'):Snapshot(memory)
            memory.write_bytes(b'SK3GSNP1'+struct.pack('<QQ',0,0xFFFFFFFFFFFFFFFF))
            with self.assertRaisesRegex(ValueError,'region'):Snapshot(memory)

    def test_capture_layout_rebase_and_exclusions(self):
        with tempfile.TemporaryDirectory() as d:
            scene,buf,item=capture_fixture(Path(d));world=import_scene(scene,buf)
            self.assertFalse(world['floor']);self.assertEqual(world['spawn'],[0,0,0])
            self.assertEqual(len(world['triangles']),2)
            for value,expected in zip(world['provenance']['source_origin_meters'],[10,2,20]):self.assertAlmostEqual(value,expected)
            self.assertEqual(world['provenance']['skipped'],{'non_static_or_overlay':1})
            self.assertAlmostEqual(world['triangles'][0]['vertices'][0][0],-15/0.0254,places=3)
            self.assertAlmostEqual(world['triangles'][0]['vertices'][0][2],-10/0.0254,places=3)
            self.assertEqual(encode(world)[:8],b'GNKWLD1\0')
            item['draws']=[[4,0,0,999]];scene.write_text(json.dumps({'generation':1,'cam':[10,5,20],'items':[item]})+'\n')
            with self.assertRaisesRegex(ValueError,'index range'):import_scene(scene,buf)
            buf.write_bytes(b'SK3BUFS1'+struct.pack('<IIQII',0,0,0,0xFFFFFFFF,0))
            with self.assertRaisesRegex(ValueError,'lengths'):import_scene(scene,buf)

    def test_half_positions_strip_and_signed_base(self):
        with tempfile.TemporaryDirectory() as d:
            scene,buf,item=capture_fixture(Path(d))
            # 4 half-float vertices; index values are offset +5, cancelled by a
            # signed guest BaseVertexIndex stored as u32 in the JSON recorder.
            points=[[-15,0,-10],[-15,0,100],[15,0,-10],[15,0,100]]
            vb=b''.join(struct.pack('>4e',*p,1) for p in points);ib=struct.pack('>4H',5,6,7,8)
            buf.write_bytes(b'SK3BUFS1'+struct.pack('<IIQII',0x1000,0x2000,0x1234,len(vb),len(ib))+vb+ib)
            item.update(pos_fmt=32,stride=8,vb_bytes=len(vb),ib_count=4,draws=[[6,0xFFFFFFFB,0,4]])
            scene.write_text(json.dumps({'generation':1,'cam':[10,5,20],'items':[item]})+'\n')
            world=import_scene(scene,buf);self.assertEqual(len(world['triangles']),2)
            self.assertFalse(world['provenance']['flipped_winding'])

    def test_obj_negative_indices_units_and_invalid_faces(self):
        with tempfile.TemporaryDirectory() as d:
            obj=Path(d)/'floor.obj';obj.write_text('v -1 0 -1\nv -1 0 1\nv 1 0 -1\nf -3/1/1 -2/2/1 -1/3/1\n')
            world=import_obj(obj,'meter',[0,0,0]);self.assertAlmostEqual(world['triangles'][0]['vertices'][0][0],-39.37008,places=4)
            obj.write_text('v 0 0 0\nf 0 1 1\n')
            with self.assertRaises(ValueError):import_obj(obj,'inch',[0,0,0])
            world['spawn'][0]=math.nan
            with self.assertRaises(ValueError):encode(world)

def native_checks(exe,runner,output):
    output.mkdir(parents=True,exist_ok=True)
    scene,buf,memory,_=snapshot_fixture(output);world=import_scene(scene,buf,memory_path=memory)
    selected=output/'imported.json';selected.write_text(json.dumps(world)+'\n')
    binary=output/'imported.gonkworld';binary.write_bytes(encode(world))
    command=[*runner,str(exe.resolve())]
    def run(path,inputs):
        r=subprocess.run([*command,'--pipe','--world',str(path.resolve())],input=inputs,capture_output=True,text=True,timeout=60)
        return r
    inputs=''.join(f'{int(i>=30)} {int(150<=i<165)} 0 0 0\n' for i in range(360))
    first=run(binary,inputs);assert first.returncode==0,first.stderr
    assert 'UNSUPPORTED' not in first.stderr,first.stderr
    assert run(binary,inputs).stdout==first.stdout,'Imported world is nondeterministic'
    rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(io.StringIO(first.stdout))]
    assert len(rows)==360 and all(all(math.isfinite(v) for v in r.values()) for r in rows)
    assert [i for i,r in enumerate(rows) if r['landed']]==[203]
    assert 60<max(r['y'] for r in rows)<66 and rows[-1]['z']>2800
    assert all(r['state'] in [0,1] and r['terrain']==1 and r['y']>=0 for r in rows)
    (output/'imported-trace.csv').write_text(first.stdout)
    # Dynamic loading must match the previous compiled-in area exactly,
    # including original rail acquisition and multi-frame rail movement.
    default=json.loads((ROOT/'worlds/test_area.json').read_text());same=output/'default.gonkworld';same.write_bytes(encode(default))
    scenario=subprocess.run([*command,'--scenario','rail'],capture_output=True,text=True,check=True,timeout=60)
    loaded=subprocess.run([*command,'--scenario','rail','--world',str(same.resolve())],capture_output=True,text=True,check=True,timeout=60)
    assert scenario.stdout==loaded.stdout,'Runtime-loaded area diverges from compiled-in world'
    # Elevated spawn and reset must retain the selected world, with no hidden
    # infinite floor masking a broken import.
    elevated=copy.deepcopy(world)
    for t in elevated['triangles']:
        for v in t['vertices']:v[1]+=120
    elevated['spawn']=[0,120,0];elev=output/'elevated.gonkworld';elev.write_bytes(encode(elevated))
    reset=run(elev,'0 0 0 0 0\n1 0 0 0 0\n0 0 0 0 0 0 1\n')
    assert reset.returncode==0,reset.stderr
    reset_rows=list(csv.DictReader(io.StringIO(reset.stdout)))
    assert len(reset_rows)==3 and all(float(r['y'])==120 for r in reset_rows)
    assert float(reset_rows[-1]['z'])==0,'Reset lost imported spawn'
    elevated['facing']=[1,0,0];elev.write_bytes(encode(elevated))
    facing=run(elev,'1 0 0 0 0\n'*60+'0 0 0 0 0 0 1\n')
    assert facing.returncode==0,facing.stderr
    facing_rows=list(csv.DictReader(io.StringIO(facing.stdout)))
    assert float(facing_rows[59]['x'])>50 and abs(float(facing_rows[59]['z']))<0.001,'Imported facing not used'
    assert float(facing_rows[-1]['x'])==0 and float(facing_rows[-1]['y'])==120,'Facing/reset lost spawn'
    # Two disjoint rails and one reversed/polyline rail use the original manager.
    multiple=copy.deepcopy(default)
    multiple['rails']=[{'points':[[-500,24,1500],[-500,24,1200],[-500,24,900]],'terrain':3},default['rails'][0]]
    multi=output/'rails.gonkworld';multi.write_bytes(encode(multiple))
    multi_result=subprocess.run([*command,'--scenario','rail','--world',str(multi.resolve())],capture_output=True,text=True,check=True,timeout=60)
    multi_rows=list(csv.DictReader(io.StringIO(multi_result.stdout)))
    assert sum(r['state']=='4' for r in multi_rows)==49
    assert all(r['rail']=='3' for r in multi_rows if r['state']=='4'),'Rail chains linked incorrectly'
    encoded=encode(world)
    for bad in [b'badmagic',encoded[:-1],encoded+b'extra',encoded[:12]+struct.pack('<I',0xFFFFFFFF)+encoded[16:],
                encoded[:24]+struct.pack('<f',math.nan)+encoded[28:]]:
        invalid=output/'invalid.gonkworld';invalid.write_bytes(bad)
        result=run(invalid,'0 0 0 0 0\n')
        assert result.returncode==2 and 'WORLD_ERROR' in result.stderr and not result.stdout,result
    (output/'summary.json').write_text(json.dumps({'passed':True,'frames':360,'apex':max(r['y'] for r in rows),
        'landing_frame':203,'compiled_world_trace_equal':True,'multi_rail_frames':49,'retail_assets_used':False},indent=2)+'\n')
    print('IMPORTED_WORLD_TEST passed: Skate-format fixture -> shared world -> real THUG push/ollie/land; reset, rail chains, deterministic replay, malformed data')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--executable',type=Path)
    p.add_argument('--runner',nargs='+',default=[]);p.add_argument('--output',type=Path,default=ROOT/'logs/world-import')
    args=p.parse_args();suite=unittest.defaultTestLoader.loadTestsFromTestCase(ImportTests)
    if not unittest.TextTestRunner().run(suite).wasSuccessful():raise SystemExit(1)
    if args.executable:native_checks(args.executable,args.runner,args.output)
