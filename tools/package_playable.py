"""Package tracked cumulative sources with the verified Windows preview tools."""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--godot-archive',type=Path,required=True)
p.add_argument('--output',type=Path,default=root.parent/'GonkSkate-v0.6.0-Windows-Playable-Full-Package.zip')
a=p.parse_args()
expected='266978b803f7532edc69bdd5d8c4fdced0ea97aef1224a8879616398a2559e135520e186add06b532aa92bdfeecf6ac024634024de4b3abd69f6c34e6d6d0563'
assert hashlib.sha512(a.godot_archive.read_bytes()).hexdigest()==expected,'Godot archive hash differs from official 4.4.1 SHA512 sums'
manifest_path=root/'build/thug-headless-windows/manifest.json';manifest=json.loads(manifest_path.read_text())
exe=root/'build/thug-headless-windows/gonkskate-thug-test.exe'
assert hashlib.sha256(exe.read_bytes()).hexdigest()==manifest['executable_sha256']
assert manifest['upstream_commit']=='98b4e24921446ccd4b157453e25697f9574f0053'
checks=json.loads((root/'logs/thug-headless-windows/summary.json').read_text())
assert checks['soak_landings']==55
files=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
version=(root/'VERSION').read_text().strip();prefix='GonkSkate-v'+version+'/'
with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
 for name in files:
  if name:bundle.write(root/name,prefix+name)
 for name in ['build/thug-headless-windows/gonkskate-thug-test.exe','build/thug-headless-windows/manifest.json',
              'logs/thug-headless/summary.json','logs/thug-headless-windows/summary.json','logs/playable-preview.png']:
  bundle.write(root/name,prefix+name)
 with zipfile.ZipFile(a.godot_archive) as engine:
  for name in engine.namelist():
   assert Path(name).name==name
   bundle.writestr(prefix+'bin/godot/'+name,engine.read(name))
print(a.output)
print('SHA256',hashlib.sha256(a.output.read_bytes()).hexdigest())
print('Bytes',a.output.stat().st_size)
