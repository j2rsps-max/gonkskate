"""Compile a C-ABI client and compare embedded real-core traces with the executable."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library",type=Path,help="Library build directory with manifest.json")
    parser.add_argument("--baseline",type=Path)
    parser.add_argument("--runner",nargs="+",default=[])
    parser.add_argument("--msvc-host",action="store_true",help="Also compile/run the no-CRT MSVC-ABI Windows host")
    args=parser.parse_args()
    folder=args.library.resolve()
    manifest=json.loads((folder/"manifest.json").read_text())
    assert manifest["mode"]=="library" and manifest["runtime_abi_version"]==1
    windows=manifest["target"]=="windows"
    baseline=(args.baseline or ROOT/("build/runtime-baseline/gonkskate-thug-test.exe" if windows else "build/runtime-baseline/gonkskate-thug-test")).resolve()
    compiler=os.environ.get("GONK_CLANG","/workspace/tooling/llvm/usr/bin/clang++-19")
    env=os.environ.copy();env["LD_LIBRARY_PATH"]="/workspace/tooling/llvm/usr/lib/x86_64-linux-gnu"
    flags=["-std=c++17","-pthread","-I"+str(ROOT/"native/thug_adapter/include")]
    if manifest["test_hooks"]:flags+=["-DGONK_THUG_RUNTIME_TESTING"]
    if windows:
        mingw=Path("/workspace/tooling/mingw/usr");gcc=mingw/"lib/gcc/x86_64-w64-mingw32/14-posix"
        flags += ["--target=x86_64-w64-windows-gnu","--sysroot="+str(mingw/"x86_64-w64-mingw32"),
                  "-I"+str(gcc/"include/c++"),"-I"+str(gcc/"include/c++/x86_64-w64-mingw32"),
                  "-L"+str(gcc),"-B"+str(mingw/"bin"),"-static","--ld-path=/workspace/tooling/llvm/usr/bin/ld.lld-19"]
        library=folder/"gonkskate-thug-runtime.lib"
    else:
        library=folder/"libgonkskate-thug-runtime.so";flags += ["-Wl,-rpath,$ORIGIN"]
    client=folder/("runtime-client.exe" if windows else "runtime-client")
    subprocess.run([compiler,*flags,str(ROOT/"native/thug_adapter/tests/runtime_test.cpp"),str(library),"-o",str(client)],env=env,check=True)
    def run(argv,**kwargs):
        return subprocess.run([*args.runner,*map(str,argv)],capture_output=True,text=True,env=env,cwd=folder,check=True,timeout=60,**kwargs)
    contract=run([client]);(folder/"contracts.log").write_text(contract.stdout+contract.stderr)
    if args.msvc_host:
        if not windows:parser.error("--msvc-host requires a Windows library")
        llvm=Path(compiler).parent
        obj=folder/"runtime-msvc-host.obj";exe=folder/"runtime-msvc-host.exe"
        resource=subprocess.check_output([str(llvm/"clang-19"),"-print-resource-dir"],env=env,text=True).strip()
        subprocess.run([str(llvm/"clang-19"),"--target=x86_64-pc-windows-msvc","-ffreestanding","-nostdinc",
            "-isystem",resource+"/include","-I"+str(ROOT/"native/thug_adapter/include"),"-c",
            str(ROOT/"native/thug_adapter/tests/runtime_msvc_host.c"),"-o",str(obj)],env=env,check=True)
        subprocess.run([str(llvm/"lld-link-19"),"/entry:mainCRTStartup","/subsystem:console","/nodefaultlib",
            "/out:"+str(exe),str(obj),str(library),str(mingw/"x86_64-w64-mingw32/lib/libkernel32.a")],env=env,check=True)
        run([exe])
    traces={}
    for scenario in ["idle","ollie","steer","soak","rail","rail_jump"]:
        original=run([baseline,"--scenario",scenario])
        rows=list(csv.DictReader(io.StringIO(original.stdout)))
        controls="".join(" ".join(r.get(key,"0") for key in ["push","crouch","left","right","brake","grind","reset"])+"\n" for r in rows)
        actual=run([client,"--trace",*(["--flat"] if not scenario.startswith("rail") else [])],input=controls)
        assert actual.stdout==original.stdout,f"Embedded/executable divergence: {scenario}"
        assert "UNSUPPORTED" not in actual.stderr
        traces[scenario]={"ticks":len(rows),"sha256":hashlib.sha256(actual.stdout.encode()).hexdigest()}
    result={"abi_version":1,"target":manifest["target"],"test_hooks":manifest["test_hooks"],
            "library_sha256":manifest["executable_sha256"],"client_sha256":hashlib.sha256(client.read_bytes()).hexdigest(),
            "native_contracts":"PASS","msvc_abi_host":"PASS" if args.msvc_host else "not run","executable_equivalence":traces,
            "scope":"Real THUG library in a native C-ABI host; no retail Skate guest executed"}
    (folder/"runtime-validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
