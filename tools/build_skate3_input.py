"""Build the host controller driver with pinned, unmodified ReXGlue InputSystem."""
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
flags=['-std=c++23','-O1','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
       '-DSPDLOG_FMT_EXTERNAL','-DFMT_HEADER_ONLY',
       '-I'+str(sdk/'include'),'-I'+str(root/'native/skate3_adapter/include')]
dependencies=['simde','fmt','spdlog','tomlplusplus','sdl3','cli11']
dependency_pins={}
for name in dependencies:
 path=sdk/'thirdparty'/name
 expected=subprocess.check_output(['git','-C',str(sdk),'ls-tree','HEAD','thirdparty/'+name],text=True).split()[2]
 assert subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()==expected,f'{name} differs from SDK pin; run scripts/setup-skate3-source.py'
 dependency_pins[name]=expected
 flags+=['-I'+str(path if name=='simde' else path/'include')]
if windows:
 mingw=Path('/workspace/tooling/mingw/usr');gcc=mingw/'lib/gcc/x86_64-w64-mingw32/14-posix'
 flags+=['--target=x86_64-w64-windows-gnu','--sysroot='+str(mingw/'x86_64-w64-mingw32'),'-I'+str(gcc/'include/c++'),'-I'+str(gcc/'include/c++/x86_64-w64-mingw32'),'-L'+str(gcc),'-B'+str(mingw/'bin'),'-static','-pthread',
         '-fuse-ld=/workspace/tooling/llvm/usr/bin/ld.lld-19']
exe=build/('gonkskate-skate3-input-test.exe' if windows else 'gonkskate-skate3-input-test')
sources=[root/'native/skate3_adapter'/name for name in [
 'src/skate3_pad.cpp','src/skate3_input.cpp','src/skate3_driver.cpp',
 'tests/pad_test.cpp','tests/driver_test.cpp']]
sources += [sdk/'src'/name for name in ['input/input_system.cpp','core/cvar.cpp','core/logging.cpp']]
# Cache separate translation units so diagnostics and cross-build fixes need not
# recompile the whole SDK. Invalidate on compiler/flags/source/header changes.
headers=list((root/'native/skate3_adapter/include').glob('*.h'))+list((sdk/'include').rglob('*.h'))
for name in dependencies:
 headers+=list((sdk/'thirdparty'/name).rglob('*.h'))+list((sdk/'thirdparty'/name).rglob('*.hpp'))
context=hashlib.sha256(subprocess.check_output([cxx,'--version'],env=env))
context.update(json.dumps(flags).encode())
for path in sorted(set(headers)):
 context.update(str(path).encode());context.update(path.read_bytes())
objects=[]
for source in sources:
 compile_flags=[f for f in flags if not f.startswith(('-Wl,','-fuse-ld='))]
 compiled_source=source
 # COFF requires symbols even in unused physical-driver factory sections. The
 # standalone Windows test omits ONLY that factory in a generated translation
 # unit. Every InputSystem method stays byte-for-byte upstream. Production CMake
 # links the complete original SDK; the reference checkout is never edited.
 if windows and source==sdk/'src/input/input_system.cpp':
  original=source.read_text()
  marker='std::unique_ptr<InputSystem> CreateDefaultInputSystem(bool tool_mode) {'
  footer='\n}  // namespace rex::input\n'
  assert original.count(marker)==1 and original.endswith(footer)
  compiled_source=build/'sdk_input_system_without_hardware_factory.cpp'
  compiled_source.write_text(original.split(marker)[0]+footer)
 key=hashlib.sha256(context.digest()+compiled_source.read_bytes()).hexdigest()
 obj=build/'objects'/(source.stem+'-'+key[:20]+'.o');obj.parent.mkdir(exist_ok=True)
 if not obj.exists():
  subprocess.run([cxx,*compile_flags,'-c',str(compiled_source),'-o',str(obj)],env=env,check=True)
 objects.append(obj)
subprocess.run([cxx,*flags,*( ['-Wl,--exclude-all-symbols'] if windows else []),*map(str,objects),'-o',str(exe)],env=env,check=True)
manifest={**pins,'target':a.target,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
 'sdk_input_header_sha256':hashlib.sha256((sdk/'include/rex/input/input.h').read_bytes()).hexdigest(),
 'dependency_pins':dependency_pins,
 'source_sha256':{str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
 'standalone_sdk_factory_omitted':windows,
 'compile_context_sha256':context.hexdigest(),
 'scope':'Host driver registered with original SDK InputSystem; no retail game code executed'}
(build/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(exe)
