"""Package the standalone PC inspection helper without engines or retail files."""
import json,subprocess,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
version=(root/'VERSION').read_text().strip()
prefix=f'GonkSkate-Reference-Check-v{version}/'
output=root.parent/f'GonkSkate-Reference-Check-v{version}.zip'
files=['RUN_SKATE3_REFERENCE.cmd','VERSION','scripts/run-skate3-reference.py',
       'tools/skate3_readiness.py','native/skate3_adapter/config/upstream.json']
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
 for name in files:archive.write(root/name,prefix+name)
 archive.write(root/'docs/REFERENCE_CHECK.md',prefix+'README.md')
 archive.writestr(prefix+'RELEASE_INFO.json',json.dumps({'version':version,
  'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
  'scope':'standalone reference inspection and console logging; uses an existing PC installation'},indent=2)+'\n')
print(output)
print('Bytes',output.stat().st_size)
