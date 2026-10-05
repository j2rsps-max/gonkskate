"""Behavioral checks for the real-core executable, independent of its build."""
import argparse, csv, hashlib, io, json, math, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('executable',type=Path)
p.add_argument('--runner',nargs='+',default=[],help='Optional executable runner, e.g. wine64')
p.add_argument('--output',type=Path,default=Path('logs/thug-headless'))
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
exe=[*a.runner,str(a.executable.resolve())]
def run(name):
 result=subprocess.run([*exe,'--scenario',name],capture_output=True,text=True,check=True,timeout=30)
 (a.output/(name+'.csv')).write_text(result.stdout)
 (a.output/(name+'.adapters.log')).write_text(result.stderr)
 assert 'UNSUPPORTED' not in result.stderr and 'ASSERT' not in result.stderr,result.stderr
 rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(io.StringIO(result.stdout))]
 for i,r in enumerate(rows):
  assert r['frame']==i and all(math.isfinite(x) for x in r.values()),(name,i,'nonfinite/frame')
  assert r['state'] in (0,1) and r['rail']==-1 and r['terrain']==1,(name,i,'unexpected state/terrain')
  assert r['y']>=0 and r['queries']>0 and r['lookups']>0,(name,i,'floor/query')
  assert r['landed']==int(i>0 and rows[i-1]['state']==1 and r['state']==0),(name,i,'landed flag')
  if i:
   d=math.hypot(r['x']-rows[i-1]['x'],r['z']-rows[i-1]['z'])
   assert d<12,(name,i,'teleport',d)
 return result.stdout,rows
idle,rows=run('idle');assert len(rows)==360 and all(r['x']==r['y']==r['z']==r['vx']==r['vy']==r['vz']==0 for r in rows)
ollie,rows=run('ollie')
assert all(r['z']==0 and r['state']==0 for r in rows[:30])
assert rows[100]['vz']>rows[30]['vz']>0 and rows[149]['state']==0
assert rows[164]['crouch']==1 and rows[164]['state']==0 and rows[165]['crouch']==0 and rows[165]['state']==1
assert rows[165]['vy']>400
assert 60<max(r['y'] for r in rows)<66
landings=[i for i,r in enumerate(rows) if r['landed']];assert landings==[203],landings
# Independent kinematic invariant: active physics.q gravity is -1350 in/s^2.
for i in range(166,203):assert abs(rows[i]['vy']-rows[i-1]['vy']+1350/60)<0.001,(i,'gravity')
assert rows[-1]['z']>2800 and rows[-1]['state']==0
repeat=subprocess.run(exe,capture_output=True,text=True,check=True,timeout=30);assert repeat.stdout==ollie,'nondeterministic replay'
steer,turn=run('steer');assert turn[-1]['x']>2000 and abs(turn[-1]['fx'])>0.5
assert math.hypot(turn[-1]['vx'],turn[-1]['vz'])==0,'brake did not stop'
soak,long=run('soak');assert len(long)==10000 and sum(r['landed'] for r in long)==55
# IPC must reproduce the same scenario, without frame-number-driven jump calls.
inputs=''.join(' '.join(str(int(r[k])) for k in ('push','crouch','left','right','brake'))+'\n' for r in rows)
stream=subprocess.run([*exe,'--pipe'],input=inputs,capture_output=True,text=True,check=True,timeout=30)
assert stream.stdout==ollie,'IPC diverges from scripted input'
bad=subprocess.run([*exe,'--pipe'],input='1 0 0 0 0\n1 2 0 0 0\n',capture_output=True,text=True,timeout=30)
assert bad.returncode==2 and 'Invalid input frame 1' in bad.stderr
probe=subprocess.run([*exe,'--probe-peripheral'],capture_output=True,text=True,timeout=30)
assert probe.returncode==3 and 'UNSUPPORTED frame=0 Obj::CManual::DoManualPhysics()' in probe.stderr,'fail-fast diagnostic missing'
summary={'tick_hz':60,'ollie_air_frame':165,'landing_frame':203,'apex_inches':max(r['y'] for r in rows),'soak_frames':10000,'soak_landings':55,'deterministic_sha256':hashlib.sha256(ollie.encode()).hexdigest(),'checks':['idle','ground acceleration','release-triggered ollie','air gravity','landing flag','no teleports','steering','braking','long-run repeated ollies','bit-identical replay','IPC equivalence','invalid input rejection','unimplemented peripheral traps']}
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
