#!/usr/bin/env python3
"""Run a separately installed upstream Skate3Recomp and capture its console output."""
import argparse,datetime,hashlib,json,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--exe',type=Path,required=True);a=p.parse_args()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f');log=ROOT/'logs'/('skate3-reference-'+stamp);log.mkdir(parents=True)
report={'scope':'separate upstream reference run; not a GonkSkate physics backend','retail_assets_bundled':False};status=0
try:
 exe=a.exe.resolve();assert exe.is_file(),'Skate3Recomp executable not found'
 with exe.open('rb') as f:report['executable_sha256']=hashlib.file_digest(f,'sha256').hexdigest() if hasattr(hashlib,'file_digest') else hashlib.sha256(f.read()).hexdigest()
 print('Starting the separately installed Skate3Recomp. Quit the game to finish the result bundle.',flush=True)
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
