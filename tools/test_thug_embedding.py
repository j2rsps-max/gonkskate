"""Stage the actual Linux production runtime and run a relocated CMake host.

This exercises the exact import/copy CMake module used by the staged Skate
frontend. It does not execute retail guest code or prove player attachment.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from stage_skate3_probe import ROOT, stage


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library",type=Path)
    parser.add_argument("--cmake",default="cmake")
    args=parser.parse_args()
    library=args.library.resolve()
    if json.loads((library/"manifest.json").read_text())["target"]!="linux":
        parser.error("Use test_thug_runtime.py --msvc-host for the Windows ABI check")
    with tempfile.TemporaryDirectory(dir=ROOT/"build") as temporary:
        folder=Path(temporary)
        staged=stage(ROOT/"external/skate3",folder/"skate",library)
        runtime=staged/"src/gonkskate_thug_runtime"
        source=folder/"host";source.mkdir()
        shutil.copyfile(ROOT/"native/thug_adapter/tests/runtime_test.cpp",source/"main.cpp")
        (source/"CMakeLists.txt").write_text('''cmake_minimum_required(VERSION 3.25)
project(embedding_fixture LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(Threads REQUIRED)
add_executable(host main.cpp)
target_link_libraries(host PRIVATE Threads::Threads)
include("${GONK_RUNTIME}/SkateThugRuntime.cmake")
gonkskate_embed_thug(host "${GONK_RUNTIME}")
''')
        binary=folder/"out"
        subprocess.run([args.cmake,"-S",str(source),"-B",str(binary),"-DGONK_RUNTIME="+str(runtime)],check=True)
        subprocess.run([args.cmake,"--build",str(binary),"--parallel","2"],check=True)
        # Neither the staged source binary nor a global build path may be
        # required at runtime. Copy just the final executable and its DLL/.so.
        relocated=folder/"relocated";relocated.mkdir()
        for name in ("host","libgonkskate-thug-runtime.so"):
            shutil.copyfile(binary/name,relocated/name)
        (relocated/"host").chmod(0o755)
        (runtime/"libgonkskate-thug-runtime.so").unlink()
        (binary/"libgonkskate-thug-runtime.so").unlink()
        result=subprocess.run([str(relocated/"host")],cwd=relocated,capture_output=True,text=True,check=True)
        (library/"frontend-embedding-validation.json").write_text(json.dumps({
            "cmake_import":"PASS","relocated_host_contracts":"PASS","staged_frontend_handshake":True,
            "retail_skate_app_built":False,"guest_gameplay_attached":False,
            "stdout":result.stdout},indent=2)+"\n")
    print("PASS: production runtime staged, CMake-linked, copied and executed from a relocated native host")


if __name__=="__main__":main()
