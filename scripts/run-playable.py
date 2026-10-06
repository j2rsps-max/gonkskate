#!/usr/bin/env python3
"""Launch the native THUG test area and preserve a diagnostic ZIP."""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys, urllib.request, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from gonk_world import load as load_world, encode as encode_world
from playable_results import failure_message
STAMP=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
LOG=ROOT/'logs'/('playable-'+STAMP);LOG.mkdir(parents=True)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--autotest',action='store_true')
parser.add_argument('--area-autotest',action='store_true')
parser.add_argument('--controller-autotest',action='store_true')
parser.add_argument('--recovery-test',action='store_true',help=argparse.SUPPRESS)
parser.add_argument('--world',type=Path,default=ROOT/'worlds/test_area.json',help='Shared normalized world JSON')
args=parser.parse_args()

def run(name,command,environment=None):
 print(f'{name}: '+str(command[0]),flush=True)
 with (LOG/(name+'.txt')).open('w') as output:
  subprocess.run(list(map(str,command)),cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,check=True,env=environment)

def godot():
 custom=os.environ.get('GONK_GODOT')
 if custom:return custom
 packaged=ROOT/'bin/godot/Godot_v4.4.1-stable_win64_console.exe'
 if sys.platform=='win32' and packaged.is_file():return str(packaged)
 existing=shutil.which('godot') or shutil.which('godot4')
 if existing:return existing
 platform='win64.exe' if sys.platform=='win32' else 'linux.x86_64'
 hashes={
 'win64.exe':'266978b803f7532edc69bdd5d8c4fdced0ea97aef1224a8879616398a2559e135520e186add06b532aa92bdfeecf6ac024634024de4b3abd69f6c34e6d6d0563',
 'linux.x86_64':'ef4e76880a514257175544952c61191106fdef3095b909bafed9fcbeb230c3e5533920a0f3012882dd4bbde83028a67549825794e2d2c3cf76eba7918b71370e'}
 name=f'Godot_v4.4.1-stable_{platform}.zip';cache=ROOT/'bin/godot';cache.mkdir(parents=True,exist_ok=True)
 archive=cache/name
 print('Downloading pinned Godot 4.4.1 from its official release...',flush=True)
 urllib.request.urlretrieve('https://github.com/godotengine/godot-builds/releases/download/4.4.1-stable/'+name,archive)
 if hashlib.sha512(archive.read_bytes()).hexdigest()!=hashes[platform]:raise RuntimeError('Godot SHA512 mismatch')
 with zipfile.ZipFile(archive) as z:
  for info in z.infolist():
   if Path(info.filename).name!=info.filename:raise RuntimeError('Unexpected archive member')
  z.extractall(cache)
 executable=cache/('Godot_v4.4.1-stable_win64_console.exe' if sys.platform=='win32' else 'Godot_v4.4.1-stable_linux.x86_64')
 if sys.platform!='win32':executable.chmod(0o755)
 return str(executable)

exit_code=0
started=datetime.datetime.now().timestamp()
world_report={}
scene_report=None
try:
 native=ROOT/('build/thug-headless-windows/gonkskate-thug-test.exe' if sys.platform=='win32' else 'build/thug-headless/gonkskate-thug-test')
 manifest=native.parent/'manifest.json'
 selected=load_world(args.world)
 world_binary=LOG/'selected-world.gonkworld';world_binary.write_bytes(encode_world(selected))
 # Freeze the exact float32 geometry sent to physics for the renderer too.
 world_json=LOG/'selected-world.json';world_json.write_text(json.dumps(selected,separators=(',',':'))+'\n')
 world_report={'name':selected.get('name','Test area'),'source_game':selected.get('source_game','synthetic'),
               'json_sha256':hashlib.sha256(world_json.read_bytes()).hexdigest(),
               'binary_sha256':hashlib.sha256(world_binary.read_bytes()).hexdigest(),
               'triangles':len(selected['triangles']),'rails':len(selected['rails'])}
 world_matches=manifest.exists() and json.loads(manifest.read_text()).get('runtime_world_version')==1
 if not native.exists() or not world_matches:
  if sys.platform=='win32':raise RuntimeError('Native executable lacks runtime world loading. Use the v0.6.6 or later Windows preview package.')
  run('build',[sys.executable,'tools/build_thug_headless.py'])
 if hashlib.sha256(native.read_bytes()).hexdigest()!=json.loads(manifest.read_text())['executable_sha256']:raise RuntimeError('Native executable hash differs from build manifest')
 run('native-checks',[sys.executable,'tools/test_thug_headless.py',native,'--output',LOG/'native'])
 engine=godot()
 probe_env=os.environ.copy();probe_env.setdefault('XDG_CACHE_HOME',str(ROOT/'bin/godot/cache'))
 probe=subprocess.check_output([engine,'--version'],text=True,env=probe_env,stderr=subprocess.STDOUT).strip().splitlines()[-1].split('.')[0:2]
 if len(probe)!=2 or (int(probe[0]),int(probe[1]))<(4,4):raise RuntimeError('Godot 4.4 or later is required for native-process pipes')
 env=os.environ.copy();env['GONK_THUG_EXE']=str(native)
 env['GONK_SCENE_RESULT']=str((LOG/'scene-result.json').resolve())
 env['GONK_WORLD_JSON']=str(world_json.resolve());env['GONK_WORLD_BINARY']=str(world_binary.resolve())
 if sys.platform!='win32':
  for key,subdir in [('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache')]:
   env.setdefault(key,str(ROOT/'bin/godot'/subdir))
 run('controller-checks',[engine,'--headless','--path',ROOT/'playable','--script','res://test_controller.gd'],env)
 command=[engine,'--path',str(ROOT/'playable')]
 if args.autotest or args.area_autotest or args.controller_autotest or args.recovery_test:command+=['--headless']
 if args.recovery_test:command+=['--script','res://test_recovery.gd']
 command+=['--']+(['--controller-autotest'] if args.controller_autotest else ['--area-autotest'] if args.area_autotest else ['--autotest'] if args.autotest else [])
 print('Starting GonkSkate. W pushes, A/D steer, S brakes, hold/release Space to ollie, E grinds, R resets.',flush=True)
 with (LOG/'scene.txt').open('w') as output:
  # Keep Python's ignored SIGPIPE on Unix: a dead physics child must produce
  # a recoverable pipe error, rather than terminate the presentation window.
  result=subprocess.run(command,cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,restore_signals=False)
 scene_text=(LOG/'scene.txt').read_text(encoding='utf-8',errors='replace')
 if (LOG/'scene-result.json').exists():scene_report=json.loads((LOG/'scene-result.json').read_text(encoding='utf-8'))
 failure=failure_message(scene_text,scene_report)
 if failure:raise RuntimeError(failure)
 if result.returncode:raise RuntimeError(f'Scene exited {result.returncode}; see {LOG/"scene.txt"}')
 if scene_report is None:raise RuntimeError('Scene exited without its session-health report; return the results ZIP')
 if (args.autotest or args.area_autotest or args.controller_autotest) and 'PLAYABLE_AUTOTEST passed' not in scene_text:raise RuntimeError('Scene did not finish its integration test')
except Exception as error:
 exit_code=1;print(str(error),file=sys.stderr);(LOG/'error.txt').write_text(str(error)+'\n')
finally:
 (LOG/'run.json').write_text(json.dumps({'version':(ROOT/'VERSION').read_text().strip(),'exit_code':exit_code,'autotest':args.autotest,'area_autotest':args.area_autotest,'controller_autotest':args.controller_autotest,'world':world_report,'scene_health':scene_report},indent=2)+'\n')
 bundle=ROOT/'logs'/f'GonkSkate-playable-results-{STAMP}.zip'
 with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
  for file in LOG.rglob('*'):
   # World data stays local: result ZIPs contain identity/counts/traces, not
   # imported retail-derived geometry.
   if file.is_file() and file.name not in ['selected-world.json','selected-world.gonkworld']:z.write(file,file.relative_to(LOG))
  for file in (ROOT/'logs').glob('playable-*.csv*'):
   if file.stat().st_mtime>=started:z.write(file,'session/'+file.name)
 print('Result bundle:',bundle,flush=True)
sys.exit(exit_code)
