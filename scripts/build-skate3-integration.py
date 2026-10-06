#!/usr/bin/env python3
"""Build the pinned Skate frontend with the production THUG DLL and probe.

Runs on the owner's Windows PC in an x64 Native Tools command prompt, using
locally supplied extracted game files and matching TU3. Never edits the installed
game. A full retail build has not been validated in the asset-free cloud.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from skate3_readiness import inspect
from stage_skate3_probe import git, stage, runtime_files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root",type=Path,required=True,help="Extracted dump containing default.xex and data/")
    tu=parser.add_mutually_exclusive_group()
    tu.add_argument("--title-update",type=Path,help="Matching local TU3 STFS package if installed patches are unavailable")
    tu.add_argument("--staged-tu-root",type=Path,help="Existing local folder with matching default.xexp and data/webkit/EAWebkit.xexp")
    parser.add_argument("--runtime",type=Path,default=ROOT/"bin/thug-runtime")
    parser.add_argument("--parallel",type=int,default=1,help="Default 1 for a 16 GB PC")
    parser.add_argument("--preflight-only",action="store_true",help="Check tools/files and export diagnostics without fetching or building")
    args=parser.parse_args()
    if not 1<=args.parallel<=16:parser.error("--parallel must be between 1 and 16")
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    log=ROOT/"logs"/("skate-integration-build-"+stamp);log.mkdir(parents=True)
    report={"schema_version":1,"retail_guest_built":False,"guest_gameplay_attached":False,
        "preflight_only":args.preflight_only,"steps":[]}
    status=0
    def run(name,command,cwd=ROOT):
        print(name+"...",flush=True)
        with (log/(name+".txt")).open("wb") as output:
            result=subprocess.run(list(map(str,command)),cwd=cwd,stdout=output,stderr=subprocess.STDOUT)
        report["steps"].append({"name":name,"exit_code":result.returncode})
        # Native stderr is diagnostic output; only exit code determines failure.
        if result.returncode:raise RuntimeError(f"{name} exited {result.returncode}; full log: {log / (name+'.txt')}")
    try:
        if sys.platform!="win32":raise RuntimeError("Full frontend helper targets Windows; Linux developers can use the documented source presets")
        for executable in ("git","cmake","ninja","clang-cl"):
            tool=shutil.which(executable)
            if not tool:raise RuntimeError(f"{executable} is missing from PATH; use an x64 Native Tools prompt with LLVM/Clang installed")
            run("version-"+executable,[tool,"--version"])
        cmake_version=re.search(r"cmake version (\d+)\.(\d+)",(log/"version-cmake.txt").read_text(errors="replace"))
        clang_version=re.search(r"clang version (\d+)",(log/"version-clang-cl.txt").read_text(errors="replace"))
        if not cmake_version or tuple(map(int,cmake_version.groups()))<(3,25):
            raise RuntimeError("This source build requires CMake 3.25 or newer")
        if not clang_version or int(clang_version.group(1))<18:
            raise RuntimeError("This source build requires Clang 18 or newer; upstream recommends LLVM/Clang 20+")
        if not os.environ.get("INCLUDE") or not os.environ.get("LIB"):
            raise RuntimeError("Open x64 Native Tools Command Prompt for VS 2022 first so clang-cl can find the Windows SDK and C++ libraries")
        game_root=args.game_root.resolve()
        update=args.title_update.resolve() if args.title_update else None
        patch_root=(args.staged_tu_root or game_root).resolve()
        report["game_files"]=inspect(game_root)
        if report["game_files"]["status"]!="FILES_DETECTED_NEED_RUNTIME_VALIDATION" or not report["game_files"].get("title_id_matches") or not report["game_files"].get("media_id_matches_tu3"):
            raise RuntimeError("Game files do not match the inspected Skate 3/TU3 profile; see game_files in report.json")
        if update:
            if not update.is_file():raise RuntimeError("The supplied TU3 STFS package is missing")
            with update.open("rb") as file:
                if file.read(4) not in (b"CON ",b"LIVE",b"PIRS"):
                    raise RuntimeError("Title update input must be the local STFS TU3 package")
        else:
            report["installed_title_update"]=inspect(patch_root)["title_update"]
            if not all(item["matches_inspected_tu3"] for item in report["installed_title_update"]):
                raise RuntimeError("Matching installed TU3 patches were not found; supply --staged-tu-root or --title-update")
        manifest,_=runtime_files(args.runtime)
        if manifest["target"]!="windows":raise RuntimeError("Use the prebuilt Windows production runtime from the development check ZIP")
        report["runtime_sha256"]=manifest["executable_sha256"]
        if not args.preflight_only:
            source=ROOT/"external/skate3"
            if source.exists() and git(source,"status","--porcelain","--untracked-files=no").strip():
                raise RuntimeError("Existing reference checkout has tracked changes; preserve/reconcile them before building")
            run("prepare-pinned-source",[sys.executable,ROOT/"scripts/setup-skate3-source.py"])
            run("prepare-sdk-submodules",["git","-C",source,"submodule","update","--init","--recursive"])
            staged=stage(source,ROOT/"build"/("skate3-integration-"+stamp),args.runtime)
            report["staged_source"]=str(staged)
            configure=["cmake","--preset","gonkskate-probe","-DCMAKE_C_COMPILER=clang-cl","-DCMAKE_CXX_COMPILER=clang-cl",
                "-DSKATE3_GAME_DATA_ROOT="+game_root.as_posix()]
            configure += ["-DSKATE3_TITLE_UPDATE_PACKAGE="+update.as_posix()] if update else ["-DGONKSKATE_STAGED_TU_ROOT="+patch_root.as_posix()]
            run("configure",configure,staged)
            build=["cmake","--build","--preset","gonkskate-probe","--parallel",str(args.parallel),"--target"]
            run("stage-title-update",[*build,"skate3-title-update-codegen-inputs"],staged)
            tu_check=inspect(staged/"out/build/gonkskate-probe/title_update_codegen")
            report["staged_title_update"]=tu_check["title_update"]
            if not all(item["matches_inspected_tu3"] for item in tu_check["title_update"]):
                raise RuntimeError("Title update payload hashes differ from inspected TU3; stopped before guest generation")
            run("generate-retail-guest",[*build,"generate-all"],staged)
            run("configure-generated",configure,staged)
            run("build-frontend",[*build,"skate3"],staged)
            exe=staged/"out/build/gonkskate-probe/skate3.exe"
            if not exe.is_file():raise RuntimeError("Build returned success but skate3.exe was not produced")
            report["retail_guest_built"]=True;report["frontend_executable"]=str(exe)
            report["frontend_sha256"]=hashlib.sha256(exe.read_bytes()).hexdigest()
            print("Built frontend:",exe,flush=True)
            print("Verify ordinary controller play first; then follow docs/SKATE3_GUEST_PROBE.md to record.",flush=True)
        report["passed"]=True
    except Exception as error:
        status=1;report["passed"]=False;report["error"]=str(error);print(str(error),file=sys.stderr,flush=True)
    finally:
        report["exit_code"]=status;(log/"report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        bundle=ROOT/"logs"/("GonkSkate-integration-build-results-"+stamp+".zip")
        with zipfile.ZipFile(bundle,"w",zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(log.iterdir()):
                # Log tails and metadata only; no executable, game, generated
                # guest source, rig, memory, or geometry enters this report.
                with path.open("rb") as file:
                    size=path.stat().st_size;file.seek(max(0,size-2*1024*1024));data=file.read()
                archive.writestr(path.name,data)
        print("Build results ZIP:",bundle,flush=True)
    return status


if __name__=="__main__":sys.exit(main())
