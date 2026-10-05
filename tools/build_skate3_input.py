"""Build the controller packet bridge against pinned, unmodified ReXGlue types."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',choices=['linux','windows'],default='linux');a=p.parse_args()
windows=a.target=='windows';checkout=root/'external/skate3';sdk=checkout/'third_party/rexglue-sdk'
pins={'skate3':'f6e0ae87fdfecbadb5c1e36c55d66a744187a3cd','sdk':'7eb0faf7787f5e01333c228b8e3f03c32f7295ea'}
for name,path in [('skate3',checkout),('sdk',sdk)]:
 assert subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()==pins[name],f'{name} differs from inspected pin'
build=root/('build/skate3-input-windows' if windows else 'build/skate3-input');build.mkdir(parents=True,exist_ok=True)
cxx=os.environ.get('GONK_CLANG','/workspace/tooling/llvm/usr/bin/clang++-19');env=os.environ.copy();env['LD_LIBRARY_PATH']='/workspace/tooling/llvm/usr/lib/x86_64-linux-gnu'
flags=['-std=c++23','-I'+str(sdk/'include'),'-I'+str(root/'native/skate3_adapter/include')]
if windows:
 mingw=Path('/workspace/tooling/mingw/usr');gcc=mingw/'lib/gcc/x86_64-w64-mingw32/14-posix'
 flags+=['--target=x86_64-w64-windows-gnu','--sysroot='+str(mingw/'x86_64-w64-mingw32'),'-I'+str(gcc/'include/c++'),'-I'+str(gcc/'include/c++/x86_64-w64-mingw32'),'-L'+str(gcc),'-B'+str(mingw/'bin'),'-static','-pthread']
exe=build/('gonkskate-skate3-input-test.exe' if windows else 'gonkskate-skate3-input-test')
subprocess.run([cxx,*flags,str(root/'native/skate3_adapter/src/skate3_pad.cpp'),str(root/'native/skate3_adapter/src/skate3_input.cpp'),str(root/'native/skate3_adapter/tests/pad_test.cpp'),'-o',str(exe)],env=env,check=True)
manifest={**pins,'target':a.target,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'sdk_input_header_sha256':hashlib.sha256((sdk/'include/rex/input/input.h').read_bytes()).hexdigest(),'scope':'SDK controller packet encoding and latest-state mailbox; no retail game code executed'}
(build/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(exe)
