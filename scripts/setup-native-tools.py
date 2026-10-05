#!/usr/bin/env python3
"""Install locally extracted, signed-repository Debian tools without root."""
import argparse, os, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--windows',action='store_true',help='Also install the Windows cross-toolchain')
p.add_argument('--verify',action='store_true',help='Also install Wine and Xvfb for validation')
a=p.parse_args()
base=Path('/workspace/tooling');apt=base/'apt';(apt/'empty').mkdir(parents=True,exist_ok=True)
for directory in ('lists/partial','archives/partial'): (apt/directory).mkdir(parents=True,exist_ok=True)
(apt/'sources.list').write_text('deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main\n')
(apt/'config').write_text('\n'.join([
 f'Dir::Etc::parts "{apt}/empty";',f'Dir::Etc::main "{apt}/nonexistent";',
 f'Dir::Etc::sourcelist "{apt}/sources.list";',f'Dir::Etc::sourceparts "{apt}/empty";',
 f'Dir::State::lists "{apt}/lists";',f'Dir::Cache::archives "{apt}/archives";',
 'APT::Get::List-Cleanup "false";',f'APT::Sandbox::User "{os.environ.get("USER","agent")}";'])+'\n')
env=os.environ.copy();env['APT_CONFIG']=str(apt/'config')
subprocess.run(['apt-get','update'],env=env,check=True)
def install(folder,packages):
 destination=base/folder;cache=destination/'packages';cache.mkdir(parents=True,exist_ok=True)
 subprocess.run(['apt-get','download',*packages],cwd=cache,env=env,check=True)
 for archive in cache.glob('*.deb'):subprocess.run(['dpkg-deb','-x',str(archive),str(destination)],check=True)
install('llvm',[name+'=1:19.1.7-3+b1' for name in ('clang-19','libclang-cpp19','libclang-common-19-dev','libllvm19')])
llvm_env=env.copy();llvm_env['LD_LIBRARY_PATH']=str(base/'llvm/usr/lib/x86_64-linux-gnu')
subprocess.run([base/'llvm/usr/bin/clang++-19','--version'],env=llvm_env,check=True)
if a.windows:
 install('mingw',['g++-mingw-w64-x86-64-posix=14.2.0-19+27+b1','gcc-mingw-w64-x86-64-posix=14.2.0-19+27+b1',
   'gcc-mingw-w64-x86-64-posix-runtime=14.2.0-19+27+b1','gcc-mingw-w64-base=14.2.0-19+27+b1',
   'mingw-w64-common=12.0.0-5','mingw-w64-x86-64-dev=12.0.0-5','binutils-mingw-w64-x86-64=2.44-3+12+b1'])
if a.verify:
 install('verify',['libwine','wine64','libz-mingw-w64','xvfb','xserver-common','libxfont2'])
 verify=base/'verify'
 # Debian wrappers contain absolute install paths; adapt only local wrappers.
 server=verify/'usr/lib/wine/wineserver'
 server.write_text('#!/bin/sh\nexec "$(dirname "$0")/wineserver64" "$@"\n');server.chmod(0o755)
 wine_share=verify/'usr/share/wine/wine'
 if not wine_share.exists():wine_share.symlink_to('.')
 import shutil
 shutil.copyfile(verify/'usr/x86_64-w64-mingw32/lib/zlib1.dll',verify/'usr/lib/x86_64-linux-gnu/wine/x86_64-windows/zlib1.dll')
print('Native tools prepared under',base)
