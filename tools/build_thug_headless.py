"""Build authentic core plus fail-fast environmental support on Linux/Clang."""
import argparse, hashlib, json, os, subprocess, sys, zlib
from pathlib import Path
from thug_q import physics_tables, uncomment
import re
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--target',choices=['linux','windows'],default='linux')
a=parser.parse_args()
windows=a.target=='windows'
build=root/('build/thug-headless-windows' if windows else 'build/thug-headless');code=build/'code'
subprocess.run([sys.executable,root/'tools/prepare_thug_headless.py',root/'external/kisak-thug',code],check=True)
g,s=physics_tables((root/'external/kisak-thug/Scripts/game/skater/physics.q').read_text())
rows=['static const Scalar scalars[] = {']
runtime_globals=json.loads((root/'native/thug_adapter/headless/profile.json').read_text())['runtime_globals']
for name,raw in {**g,**s,**{k.lower():v for k,v in runtime_globals.items()}}.items():
 try: value=float(raw)
 except ValueError:continue
 rows.append(f'{{0x{zlib.crc32(name.encode())^0xffffffff:08x}, "{name}", {value!r}f}},')
rows+=['};','static const char* stat_names[] = {']
for p in json.loads((root/'native/thug_adapter/config/thug_scripted_stats.json').read_text())['parameters']:
 rows.append(json.dumps(p['name'])+',')
rows+=['};']
(build/'physics_scalars.inc').write_text('\n'.join(rows))
text=uncomment((root/'external/kisak-thug/Scripts/game/skater/grindlist.q').read_text())
start=text.index('[',text.index('GrindTrickList='))
names=re.findall(r'\bTrick_\w+',text[start:])
assert len(names)==9*16,len(names)
(build/'grind_table.inc').write_text('static const char* grind_table[9][16]={\n'+',\n'.join('{'+','.join(json.dumps(n) for n in names[i:i+16])+'}' for i in range(0,144,16))+'\n};\n')
world=json.loads((root/'worlds/test_area.json').read_text())
assert world['schema_version']==1 and world['units']=='inch'
triangles=['static const GonkThugTriangle test_triangles[]={']
for t in world['triangles']:
 assert len(t['vertices'])==3 and all(len(v)==3 for v in t['vertices'])
 triangles.append('{ {'+','.join('{'+','.join(str(float(c))+'f' for c in v)+'}' for v in t['vertices'])+'},'+str(t['flags'])+','+str(t['terrain'])+'},')
triangles+=['};']
rail=world['rails'][0];assert len(rail['points'])==2
triangles+=['static const float test_rail[2][3]={'+','.join('{'+','.join(str(float(c))+'f' for c in v)+'}' for v in rail['points'])+'};',f"static const int test_rail_terrain={rail['terrain']};"]
(build/'test_world.inc').write_text('\n'.join(triangles)+'\n')
environ=os.environ.copy();environ['LD_LIBRARY_PATH']='/workspace/tooling/llvm/usr/lib/x86_64-linux-gnu'
cxx=os.environ.get('GONK_CLANG','/workspace/tooling/llvm/usr/bin/clang++-19')
flags=['-std=c++17','-fms-extensions','-fdelayed-template-parsing','-D__PLAT_GONK__','-ffunction-sections','-fdata-sections','-Wno-register','-Wno-writable-strings','-Wno-comment','-Wno-extra-tokens','-Wno-string-plus-int', '-I'+str(code),'-I'+str(code/'sk'),'-I'+str(build),'-I'+str(root/'native/thug_adapter/include')]
if windows:
 mingw=Path(os.environ.get('GONK_MINGW','/workspace/tooling/mingw/usr'))
 gcc=mingw/'lib/gcc/x86_64-w64-mingw32/14-posix'
 flags += ['--target=x86_64-w64-windows-gnu','--sysroot='+str(mingw/'x86_64-w64-mingw32'),
           '-I'+str(gcc/'include/c++'),'-I'+str(gcc/'include/c++/x86_64-w64-mingw32'),'-L'+str(gcc),'-B'+str(mingw/'bin')]
units=['sk/components/skatercorephysicscomponent.cpp','sk/components/skaterstatecomponent.cpp','sk/components/skaterrotatecomponent.cpp','gel/object/basecomponent.cpp','gel/object/refcounted.cpp','core/math/vector.cpp','core/math/matrix.cpp','core/math/slerp.cpp','core/math/geometry.cpp','core/math/math.cpp','core/crc.cpp','gel/scripting/vecpair.cpp','sk/objects/skaterbutton.cpp','sk/objects/skaterpad.cpp','sk/objects/rail.cpp']
header_hash=hashlib.sha256(repr(flags).encode())
header_hash.update(subprocess.check_output([cxx,'--version'],env=environ))
for header in sorted((root/'native/thug_adapter/include').glob('*.h')):
 header_hash.update(header.read_bytes())
for header in sorted(code.rglob('*')):
 if header.suffix in ('.h','.inl'):header_hash.update(header.read_bytes())
header_hash.update((build/'physics_scalars.inc').read_bytes())
header_hash.update((build/'grind_table.inc').read_bytes())
header_hash.update((build/'test_world.inc').read_bytes())
objects=[]
for unit in [code/u for u in units]+[root/'native/thug_adapter/headless/runtime.cpp',root/'native/thug_adapter/headless/main.cpp',root/'native/thug_adapter/headless/rail_runtime.cpp',root/'native/thug_adapter/src/thug_params.cpp',root/'native/thug_adapter/src/thug_flat_world.cpp',root/'native/thug_adapter/src/thug_mesh_world.cpp']:
 obj=build/(unit.stem+'.o');objects.append(obj)
 digest=hashlib.sha256(header_hash.digest()+unit.read_bytes()).hexdigest()
 stamp=obj.with_suffix('.sha256')
 if obj.exists() and stamp.exists() and stamp.read_text()==digest:continue
 with (build/(unit.stem+'.compile.log')).open('w') as log:
  r=subprocess.run([cxx,*flags,'-c',str(unit),'-o',str(obj)],env=environ,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:print(log.name);raise SystemExit(r.returncode)
 stamp.write_text(digest)
print('Compiled',len(objects),'translation units')
# Keep the full component linked. Every unresolved peripheral function traps,
# names itself, and exits nonzero if a test reaches it. No silent weak no-ops.
def symbols(option):
 result=subprocess.check_output(['nm',option,*map(str,objects)],text=True)
 return {line.split()[-1] for line in result.splitlines() if line.split() and not line.endswith(':')}
missing=sorted(symbols('-u')-symbols('--defined-only'))
traps=[]
for name in missing:
 if not name.startswith('_Z') or name.startswith(('_ZSt','_ZNSt','_ZNKSt','_ZTI','_ZTV')):continue
 demangled=subprocess.check_output(['c++filt',name],text=True).strip()
 if '(' not in demangled or demangled.startswith(('std::', '__gnu_cxx::', 'operator ')):continue
 register='%rcx' if windows else '%rdi'
 directive=f'.def {name}; .scl 2; .type 32; .endef' if windows else f'.type {name},@function'
 traps += [f'.section .rdata\nlabel_{len(traps)}: .asciz "{demangled}"' if windows else f'.section .rodata\nlabel_{len(traps)}: .asciz "{demangled}"',
           f'.text\n{".globl" if windows else ".weak"} {name}\n{directive}\n{name}:\nleaq label_{len(traps)}(%rip), {register}\njmp gonk_unexpected_symbol']
(build/'traps.S').write_text('\n'.join(traps)+('' if windows else '\n.section .note.GNU-stack,"",@progbits\n'))
subprocess.run([cxx,*flags,'-c',str(build/'traps.S'),'-o',str(build/'traps.o')],env=environ,check=True)
executable=build/('gonkskate-thug-test.exe' if windows else 'gonkskate-thug-test')
subprocess.run([cxx,*flags,*map(str,objects),str(build/'traps.o'),'-Wl,--gc-sections',*(['-static','-pthread'] if windows else []),'-o',str(executable)],env=environ,check=True)
manifest={'upstream_commit':subprocess.check_output(['git','-C',str(root/'external/kisak-thug'),'rev-parse','HEAD'],text=True).strip(),
          'world_sha256':hashlib.sha256((root/'worlds/test_area.json').read_bytes()).hexdigest(),'target':a.target,'tick_hz':60,'units':[str(u.relative_to(root)) for u in [code/u for u in units]],
          'core_source_sha256':hashlib.sha256((root/'external/kisak-thug/Code/Sk/Components/SkaterCorePhysicsComponent.cpp').read_bytes()).hexdigest(),
          'executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
          'fail_fast_symbols':[subprocess.check_output(['c++filt',n],text=True).strip() for n in missing if any(f'{".globl" if windows else ".weak"} {n}\n' in t for t in traps)]}
(build/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(executable)
