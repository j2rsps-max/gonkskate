#!/usr/bin/env python3
"""Launch the native THUG test area and preserve a diagnostic ZIP."""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys, urllib.request, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STAMP=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
LOG=ROOT/'logs'/('playable-'+STAMP);LOG.mkdir(parents=True)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--autotest',action='store_true')
parser.add_argument('--area-autotest',action='store_true')
parser.add_argument('--controller-autotest',action='store_true')
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
try:
 native=ROOT/('build/thug-headless-windows/gonkskate-thug-test.exe' if sys.platform=='win32' else 'build/thug-headless/gonkskate-thug-test')
 manifest=native.parent/'manifest.json'
 world_hash=hashlib.sha256((ROOT/'worlds/test_area.json').read_bytes()).hexdigest()
 world_matches=manifest.exists() and json.loads(manifest.read_text()).get('world_sha256')==world_hash
 if not native.exists() or not world_matches:
  if sys.platform=='win32':raise RuntimeError('Native executable missing or world data changed. Use the matching Windows preview package or rebuild the native target on Linux; see docs/TEST_AREA_PROGRESS.md.')
  run('build',[sys.executable,'tools/build_thug_headless.py'])
 run('native-checks',[sys.executable,'tools/test_thug_headless.py',native,'--output',LOG/'native'])
 engine=godot()
 probe_env=os.environ.copy();probe_env.setdefault('XDG_CACHE_HOME',str(ROOT/'bin/godot/cache'))
 probe=subprocess.check_output([engine,'--version'],text=True,env=probe_env,stderr=subprocess.STDOUT).strip().splitlines()[-1].split('.')[0:2]
 if len(probe)!=2 or (int(probe[0]),int(probe[1]))<(4,4):raise RuntimeError('Godot 4.4 or later is required for native-process pipes')
 env=os.environ.copy();env['GONK_THUG_EXE']=str(native)
 if sys.platform!='win32':
  for key,subdir in [('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache')]:
   env.setdefault(key,str(ROOT/'bin/godot'/subdir))
 run('controller-checks',[engine,'--headless','--path',ROOT/'playable','--script','res://test_controller.gd'],env)
 command=[engine,'--path',str(ROOT/'playable')]
 if args.autotest or args.area_autotest or args.controller_autotest:command+=['--headless']
 command+=['--']+(['--controller-autotest'] if args.controller_autotest else ['--area-autotest'] if args.area_autotest else ['--autotest'] if args.autotest else [])
 print('Starting GonkSkate. W pushes, A/D steer, S brakes, hold/release Space to ollie, E grinds, R resets.',flush=True)
 with (LOG/'scene.txt').open('w') as output:
  result=subprocess.run(command,cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT)
 if result.returncode:raise RuntimeError(f'Scene exited {result.returncode}; see {LOG/"scene.txt"}')
 if (args.autotest or args.area_autotest or args.controller_autotest) and 'PLAYABLE_AUTOTEST passed' not in (LOG/'scene.txt').read_text():raise RuntimeError('Scene did not finish its integration test')
except Exception as error:
 exit_code=1;print(str(error),file=sys.stderr);(LOG/'error.txt').write_text(str(error)+'\n')
finally:
 (LOG/'run.json').write_text(json.dumps({'version':(ROOT/'VERSION').read_text().strip(),'exit_code':exit_code,'autotest':args.autotest,'area_autotest':args.area_autotest,'controller_autotest':args.controller_autotest},indent=2)+'\n')
 bundle=ROOT/'logs'/f'GonkSkate-playable-results-{STAMP}.zip'
 with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
  for file in LOG.rglob('*'):
   if file.is_file():z.write(file,file.relative_to(LOG))
  for file in (ROOT/'logs').glob('playable-*.csv*'):
   if file.stat().st_mtime>=started:z.write(file,'session/'+file.name)
 print('Result bundle:',bundle,flush=True)
sys.exit(exit_code)
