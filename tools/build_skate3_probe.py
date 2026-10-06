"""Compile selected real upstream wrappers with synthetic imports and real PPCContext.

This validates hook transparency, not retail gameplay or discovered physics hooks.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from stage_skate3_probe import ROOT, HOOKS, SKATE_PIN, SDK_PIN, git, function_span, patch_render

PRELUDE = r'''
#include "rex/ppc/context.h"
#include "skate3_probe.h"
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace gonkskate::probe;
std::vector<uint32_t> effects;
uint32_t pack_owner=17;
namespace skate3::native_render {
bool Enabled() { return true; }
void OnFrameEnd(uint8_t*) { effects.push_back(1); }
}
namespace skate3::native_palette {
uint32_t ExchangePackOwner(uint32_t owner) { effects.push_back(owner);auto old=pack_owner;pack_owner=owner;return old; }
}
namespace skate3::native_entity {
enum class EntClass { kSkater,kColorized,kCac,kSkaterAux };
void OnBindClass(uint32_t entity,EntClass kind) { effects.push_back(entity);effects.push_back(static_cast<uint32_t>(kind)); }
void OnRopaDoubleBuffer(uint8_t*,uint32_t entity,uint32_t index) { effects.push_back(entity);effects.push_back(index); }
void OnEntityViewAdd(uint32_t entity) { effects.push_back(entity); }
void OnEntityViewRemove(uint32_t entity) { effects.push_back(entity); }
}
std::vector<uint8_t>* guest=nullptr;
unsigned copies=0;
namespace skate3::native_scene {
bool GuestTryCopy(void* dst,const void* src,size_t size) {
  ++copies;
  const auto start=reinterpret_cast<uintptr_t>(guest->data()),address=reinterpret_cast<uintptr_t>(src);
  if(address<start || address-start>guest->size() || size>guest->size()-(address-start))return false;
  std::memcpy(dst,src,size);return true;
}
}
void Check(bool condition,const char* what) { if(!condition)throw std::runtime_error(what); }
bool FaultCopy(void*,const void*,size_t) { return false; }
bool UnstableCopy(void* dst,const void* src,size_t size) {
  static unsigned calls=0;std::memcpy(dst,src,size);
  if(++calls%2==0)static_cast<uint8_t*>(dst)[0]^=1;
  return true;
}
void Matrix(std::vector<uint8_t>& memory) {
  const std::array<float,16> matrix{1,0,0,10,0,1,0,2,0,0,1,-4,0,0,0,1};
  for(size_t i=0;i<16;++i) {
    auto bits=std::bit_cast<uint32_t>(matrix[i]);
    for(size_t b=0;b<4;++b)memory[0x10000+416+4*i+b]=uint8_t(bits>>(24-8*b));
  }
}
'''

TEST = r'''
int main(int argc,char**) {
 try {
  std::vector<uint8_t> memory(0x20000);guest=&memory;Matrix(memory);
  auto good=Snapshot(skate3::native_scene::GuestTryCopy,memory.data(),0x10000,Kind::bind_cac,0,1);
  Check(good.pose_status==PoseStatus::valid && good.rows[3]==10,"Guarded BE world snapshot failed");
  Check(Snapshot(FaultCopy,memory.data(),0x10000,Kind::bind_cac,0,0).pose_status==PoseStatus::unreadable,"Unreadable guest range");
  Check(Snapshot(UnstableCopy,memory.data(),0x10000,Kind::bind_cac,0,0).pose_status==PoseStatus::unstable,"Concurrent guest mutation");
  auto old_copies=copies;
  Snapshot(skate3::native_scene::GuestTryCopy,memory.data(),0xffffffff,Kind::bind_cac,0,0);
  Check(copies==old_copies,"Invalid guest pointer reached read callback");
  copies=0;
  gonkskate::guest_probe::Start();
  for(const auto& pair:pairs) {
    PPCContext actual{},expected{};
    actual.r3.u32=0x10000;actual.r4.u32=0x10000;actual.lr=0x82012340;actual.r17.u64=0xBADF00D;
    std::memcpy(&expected,&actual,sizeof(actual));
    effects.clear();pair.baseline(expected,memory.data());
    const auto baseline_effects=effects;
    const auto baseline_memory=memory;
    --memory[0x18000];effects.clear();
    pair.instrumented(actual,memory.data());
    Check(std::memcmp(&actual,&expected,sizeof(actual))==0,"Hook changed PPC registers");
    Check(memory==baseline_memory,"Hook changed guest memory");
    Check(effects==baseline_effects,"Hook changed original call/renderer/palette ordering");
    Check(pack_owner==17,"Palette owner was not restored");
  }
  gonkskate::guest_probe::Stop();
  if(argc==1)Check(copies==0,"Disabled probe read guest memory");
  else Check(copies==20,"Enabled probe did not read exactly ten poses twice");
  const auto stopped_copies=copies;
  gonkskate::guest_probe::Observe(memory.data(),0x10000,Kind::bind_skater,0x82783D68,0);
  Check(copies==stopped_copies,"Stopped probe still read guest memory");
  std::cout<<"All 10 real wrapper bodies preserve imports, registers, memory and renderer/palette ordering\n";
  return 0;
 } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
'''


def fixture(source):
    original = git(source, "show", "HEAD:src/skate3_native_render.cpp").decode()
    patched = patch_render(original)
    text = PRELUDE
    for address in HOOKS:
        text += f'''\nextern "C" REX_FUNC(__imp__sub_{address}) {{
  effects.push_back(0x{address});++base[0x18000];
  ctx.r3.u32=0xDEAD;ctx.r4.u32=0xBEEF;ctx.lr=0x82098760;ctx.r17.u64^=0x777;
}}
'''
        for body, baseline in [(original, True), (patched, False)]:
            start, _, end = function_span(body, address)
            wrapper = body[start:end]
            if baseline:
                wrapper = wrapper.replace(f"REX_FUNC(sub_{address})", f"REX_FUNC(baseline_sub_{address})")
            text += wrapper+"\n"
    text += "\nstruct Pair { PPCFunc* baseline;PPCFunc* instrumented; };\nconst Pair pairs[]={\n"
    text += ",\n".join(f"{{baseline_sub_{address},sub_{address}}}" for address in HOOKS)
    return text+"\n};\n"+TEST


def build(target):
    checkout=ROOT/"external/skate3"
    sdk=checkout/"third_party/rexglue-sdk"
    for path, pin in [(checkout, SKATE_PIN), (sdk, SDK_PIN)]:
        if git(path,"rev-parse","HEAD").decode().strip()!=pin:
            raise ValueError("Source differs from inspected pin")
        if git(path,"status","--porcelain","--untracked-files=no").strip():
            raise ValueError("Reference source has tracked changes; left untouched")
    simde=sdk/"thirdparty/simde"
    simde_pin=git(sdk,"ls-tree","HEAD","thirdparty/simde").decode().split()[2]
    if git(simde,"rev-parse","HEAD").decode().strip()!=simde_pin:
        raise ValueError("simde differs from inspected SDK submodule pin")
    windows=target=="windows"
    directory=ROOT/"build"/("skate3-probe-windows" if windows else "skate3-probe-hooks")
    directory.mkdir(parents=True,exist_ok=True)
    generated=directory/"wrapper_fixture.cpp"
    generated.write_text(fixture(checkout),encoding="utf-8",newline="\n")
    compiler=os.environ.get("GONK_CLANG","/workspace/tooling/llvm/usr/bin/clang++-19")
    flags=["-std=c++23","-O1","-pthread","-Wall","-Wextra",
           "-I"+str(sdk/"include"),"-I"+str(sdk/"thirdparty/simde"),
           "-I"+str(ROOT/"native/skate3_probe/include"),"-I"+str(ROOT/"native/skate3_probe/integration")]
    if windows:
        mingw=Path("/workspace/tooling/mingw/usr")
        gcc=mingw/"lib/gcc/x86_64-w64-mingw32/14-posix"
        flags += ["--target=x86_64-w64-windows-gnu","--sysroot="+str(mingw/"x86_64-w64-mingw32"),
                  "-I"+str(gcc/"include/c++"),"-I"+str(gcc/"include/c++/x86_64-w64-mingw32"),
                  "-L"+str(gcc),"-B"+str(mingw/"bin"),"-static",
                  "--ld-path=/workspace/tooling/llvm/usr/bin/ld.lld-19"]
    env=os.environ.copy()
    env["LD_LIBRARY_PATH"]="/workspace/tooling/llvm/usr/lib/x86_64-linux-gnu"
    suffix=".exe" if windows else ""
    for name, sources in [
        ("probe-hooks",[generated,ROOT/"native/skate3_probe/integration/skate3_probe.cpp"]),
        ("probe-contract",[ROOT/"native/skate3_probe/tests/probe_test.cpp"])]:
        subprocess.run([compiler,*flags,str(ROOT/"native/skate3_probe/src/probe.cpp"),
                        *map(str,sources),"-o",str(directory/(name+suffix))],env=env,check=True)
    manifest={"skate3_commit":SKATE_PIN,"sdk_commit":SDK_PIN,"simde_commit":simde_pin,"target":target,
              "retail_code_executed":False,"scope":"Selected original wrapper bodies and actual SDK PPCContext, with synthetic imports",
              "fixture_sha256":hashlib.sha256(generated.read_bytes()).hexdigest(),
              "source_sha256":{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (ROOT/"native/skate3_probe").rglob("*") if p.is_file()},
              "executables":{name:hashlib.sha256((directory/(name+suffix)).read_bytes()).hexdigest()
                             for name in ["probe-hooks","probe-contract"]}}
    (directory/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(directory)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target",choices=["linux","windows"],default="linux")
    build(parser.parse_args().target)
