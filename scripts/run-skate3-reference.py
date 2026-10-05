#!/usr/bin/env python3
"""Run a separately installed upstream Skate3Recomp and capture its console output."""
import argparse,datetime,hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from skate3_readiness import inspect
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--exe',type=Path);p.add_argument('--inspect-only',action='store_true');a=p.parse_args()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f');log=ROOT/'logs'/('skate3-reference-'+stamp);log.mkdir(parents=True)
report={'tool_version':(ROOT/'VERSION').read_text().strip() if (ROOT/'VERSION').is_file() else '0.6.4','scope':'separate upstream reference run; not a GonkSkate physics backend','retail_assets_bundled':False,'inspect_only':a.inspect_only};status=0
try:
 if a.exe is None:
  if sys.platform!='win32':raise RuntimeError('Automatic discovery is Windows-only; provide --exe.')
  script="[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding; $items = @(Get-Process -Name skate3 -ErrorAction SilentlyContinue | Where-Object { $_.Path } | Select-Object Id,Path); ConvertTo-Json -Compress -InputObject $items"
  found=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],encoding='utf-8',timeout=15).strip())
  if len(found)!=1:raise RuntimeError('Keep one Skate3Recomp window open, or provide --exe with its path.')
  a.exe=Path(found[0]['Path']);report['discovered_running_process']=True
 exe=a.exe.resolve();assert exe.is_file(),'Skate3Recomp executable not found'
 report['executable_name']=exe.name
 roots=[('beside_executable',exe.parent/'game'),('executable_directory',exe.parent)]
 if os.environ.get('APPDATA'):roots.append(('appdata_game',Path(os.environ['APPDATA'])/'skate3/game'))
 report['game_locations']={label:inspect(root) for label,root in roots if (root/'default.xex').is_file()}
 report['game_location_found']=bool(report['game_locations'])
 with exe.open('rb') as f:report['executable_sha256']=hashlib.file_digest(f,'sha256').hexdigest() if hasattr(hashlib,'file_digest') else hashlib.sha256(f.read()).hexdigest()
 if a.inspect_only:
  print('Inspected the installed reference. The running game was left open.',flush=True)
 else:
  print('Starting the separately installed Skate3Recomp. Quit the game to finish the result bundle.',flush=True)
 if not a.inspect_only:
  with (log/'console.txt').open('w') as output:
   result=subprocess.run([str(exe)],cwd=exe.parent,stdout=output,stderr=subprocess.STDOUT)
  report['reference_exit_code']=result.returncode
  if result.returncode:status=1
except Exception as e:
 report['error']=str(e);status=1;print(str(e),file=sys.stderr)
finally:
 report['exit_code']=status;(log/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 bundle=ROOT/'logs'/('GonkSkate-skate3-reference-results-'+stamp+'.zip')
 with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
  for f in log.iterdir():z.write(f,f.name)
 print('Result bundle:',bundle,flush=True)
sys.exit(status)
