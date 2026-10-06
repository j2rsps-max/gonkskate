"""Resolve the packaged or checksum-verified official Godot runtime."""
import hashlib, os, shutil, sys, urllib.request, zipfile
from pathlib import Path

def godot(root):
 custom=os.environ.get('GONK_GODOT')
 if custom:return custom
 packaged=root/'bin/godot/Godot_v4.4.1-stable_win64_console.exe'
 if sys.platform=='win32' and packaged.is_file():return str(packaged)
 existing=shutil.which('godot') or shutil.which('godot4')
 if existing:return existing
 platform='win64.exe' if sys.platform=='win32' else 'linux.x86_64'
 hashes={
 'win64.exe':'266978b803f7532edc69bdd5d8c4fdced0ea97aef1224a8879616398a2559e135520e186add06b532aa92bdfeecf6ac024634024de4b3abd69f6c34e6d6d0563',
 'linux.x86_64':'ef4e76880a514257175544952c61191106fdef3095b909bafed9fcbeb230c3e5533920a0f3012882dd4bbde83028a67549825794e2d2c3cf76eba7918b71370e'}
 name=f'Godot_v4.4.1-stable_{platform}.zip';cache=root/'bin/godot';cache.mkdir(parents=True,exist_ok=True)
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
