#!/usr/bin/env python3
"""Capture controller diagnostics and inspect optional local Skate 3 game files."""
import argparse,datetime,hashlib,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from skate3_readiness import inspect
from skate3_packet_trace import convert
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-root',type=Path);p.add_argument('--autotest',action='store_true');a=p.parse_args()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f');log=ROOT/'logs'/('skate3-check-'+stamp);log.mkdir(parents=True)
started=datetime.datetime.now().timestamp();status=0
report={'version':(ROOT/'VERSION').read_text().strip(),'synthetic_controller_test':a.autotest,'authentic_skate_gameplay_running':False}
def run(name,command,env=None):
 with (log/(name+'.txt')).open('w') as out:subprocess.run(list(map(str,command)),cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=(600 if name=='build' else 60) if a.autotest else None)
try:
 report['game_files']=inspect(a.game_root)
 native=ROOT/('build/skate3-input-windows/gonkskate-skate3-input-test.exe' if sys.platform=='win32' else 'build/skate3-input/gonkskate-skate3-input-test')
 if not native.is_file():
  if sys.platform=='win32':raise RuntimeError('Use the full Windows test package, which includes the input bridge executable.')
  run('build',[sys.executable,'tools/build_skate3_input.py'])
 manifest=json.loads((native.parent/'manifest.json').read_text());assert hashlib.sha256(native.read_bytes()).hexdigest()==manifest['executable_sha256'],'Input bridge hash differs from manifest'
 report['input_bridge']=manifest;run('native-sdk-check',[native])
 packaged=ROOT/'bin/godot/Godot_v4.4.1-stable_win64_console.exe'
 engine=os.environ.get('GONK_GODOT') or (str(packaged) if sys.platform=='win32' and packaged.is_file() else shutil.which('godot') or shutil.which('godot4'))
 if not engine:raise RuntimeError('Godot is missing. Use the full Windows package or set GONK_GODOT to Godot 4.4 or later.')
 env=os.environ.copy();env['GONK_CONTROLLER_LAB_TRACE']=str(log/'controller.jsonl')
 if sys.platform!='win32':
  for key,name in [('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache')]:env.setdefault(key,str(ROOT/'bin/godot'/name))
 run('controller-mapping-check',[engine,'--headless','--path',ROOT/'playable','--script','res://test_controller.gd'],env)
 command=[engine,'--path',str(ROOT/'playable')]
 if a.autotest:command+=['--headless']
 command+=['res://controller_lab.tscn','--']+(['--lab-autotest'] if a.autotest else [])
 print('Controller lab: move both sticks and triggers, press buttons, disconnect/reconnect, then press Esc.',flush=True)
 run('controller-lab',command,env)
 if a.autotest:assert 'CONTROLLER_LAB_AUTOTEST passed' in (log/'controller-lab.txt').read_text(encoding='utf-8',errors='replace'),'Controller lab did not finish'
 trace=log/'controller.jsonl'
 assert trace.is_file(),'Controller lab did not save its trace'
 report['samples']=convert(trace,native,log/'skate3-guest-packets.jsonl')
 records=[json.loads(s) for s in trace.read_text(encoding='utf-8').splitlines()];connected=[s for s in records if s['device']>=0]
 report['controller_observation']='CONNECTED_SAMPLES_CAPTURED' if connected else 'NO_CONTROLLER_DETECTED'
 report['disconnect_events']=sum(bool(s['disconnected']) for s in records)
 report['axis_ranges']={name+'_'+axis:[min(s[name][i] for s in records),max(s[name][i] for s in records)] for name in ['left_stick_raw','right_stick_raw'] for i,axis in enumerate(['x','y'])}
 report['buttons_seen']=0
 for record in records:report['buttons_seen'] |= record['buttons']
 report['trigger_ranges']={name:[min(s[name] for s in records),max(s[name] for s in records)] for name in ['left_trigger','right_trigger']}
 if a.autotest:
  assert len(records)==180 and report['disconnect_events']==1
  assert len(connected)==170 and all(report['trigger_ranges'][k][1]>0.99 for k in report['trigger_ranges'])
except Exception as e:
 status=1;report['error']=str(e);print(str(e),file=sys.stderr)
finally:
 report['exit_code']=status;(log/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 bundle=ROOT/'logs'/('GonkSkate-skate3-check-results-'+stamp+'.zip')
 with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
  for f in log.rglob('*'):
   if f.is_file():z.write(f,f.relative_to(log))
 print('Result bundle:',bundle,flush=True)
sys.exit(status)
