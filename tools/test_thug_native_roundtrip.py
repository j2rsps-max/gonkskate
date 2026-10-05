"""Check a recorded presentation session against an independent native replay."""
import argparse,csv,io,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('trace',type=Path);p.add_argument('executable',type=Path);a=p.parse_args()
text=a.trace.read_text();rows=list(csv.DictReader(io.StringIO(text)))
assert rows,'No session frames'
inputs=''.join(' '.join(r[k] for k in ['push','crouch','left','right','brake','grind','reset'] if k in r)+'\n' for r in rows)
r=subprocess.run([str(a.executable.resolve()),'--pipe'],input=inputs,capture_output=True,text=True,check=True,timeout=30)
assert r.stdout==text,'Presentation session does not match authoritative native replay'
print('PASS presentation/native roundtrip:',len(rows),'ticks')
