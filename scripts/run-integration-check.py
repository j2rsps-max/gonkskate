#!/usr/bin/env python3
"""Check the embedded THUG runtime and optionally import one local THUG rig."""
import argparse
import csv
import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from import_thug_rig import parse, MAX_BONES
from stage_skate3_probe import runtime_files

EXPECTED={
    "ollie":"1ebe3402ad16e524f301e881f73d0dccfad120f5818de9ed2db0a0ec30e653e2",
    "rail":"a1ba3b9eebb3ac894323e3fb7fb81ff5998a5e9447b182c7e32a756783a20bfb"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skeleton",type=Path,nargs="?",help="Optional local SKE v2 little-endian file")
    parser.add_argument("--runtime",type=Path)
    parser.add_argument("--runner",nargs="+",default=[])
    args=parser.parse_args()
    folder=(args.runtime or (ROOT/"bin/thug-runtime" if (ROOT/"bin/thug-runtime").exists() else
        ROOT/("build/thug-runtime-windows" if sys.platform=="win32" else "build/thug-runtime"))).resolve()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    log=ROOT/"logs"/("integration-check-"+stamp);log.mkdir(parents=True)
    report={"schema_version":1,"scope":"native THUG library and optional local character rig",
        "live_skate_player_control":False,"character_mesh_imported":False,"character_animations_imported":False}
    status=0
    try:
        manifest,_=runtime_files(folder)
        windows=manifest["target"]=="windows"
        client=folder/("runtime-client.exe" if windows else "runtime-client")
        validation=json.loads((folder/"runtime-validation.json").read_text())
        if validation.get("library_sha256")!=manifest["executable_sha256"] or validation.get("client_sha256")!=hashlib.sha256(client.read_bytes()).hexdigest():
            raise ValueError("Runtime/client validation hashes differ; use the tested development package")
        report["runtime"]={"abi_version":1,"target":manifest["target"],"tick_hz":60,
            "library_sha256":manifest["executable_sha256"],"upstream_commit":manifest["upstream_commit"]}
        def run(name,argv,input=None):
            result=subprocess.run([*args.runner,str(client),*argv],input=input,capture_output=True,timeout=60,cwd=folder)
            (log/(name+".stdout.txt")).write_bytes(result.stdout)
            (log/(name+".stderr.txt")).write_bytes(result.stderr)
            if result.returncode:raise RuntimeError(f"{name} failed with exit code {result.returncode}; see session logs")
            return result.stdout.replace(b"\r\n",b"\n")
        run("native-contracts",[])
        report["native_contracts"]="PASS";report["scenarios"]={}
        for scenario in ("ollie","rail"):
            controls="".join(f"{int(frame>=30)} {int(150<=frame<165)} 0 0 0 {int(scenario=='rail' and frame>=165)} 0\n" for frame in range(360))
            argv=["--trace"]+(["--flat"] if scenario=="ollie" else [])
            first=run(scenario,argv,controls.encode())
            repeat=run(scenario+"-replay",argv,controls.encode())
            digest=hashlib.sha256(first).hexdigest()
            if first!=repeat or digest!=EXPECTED[scenario]:
                raise RuntimeError(f"{scenario} diverged from the authentic executable baseline")
            rows=list(csv.DictReader(io.StringIO(first.decode())))
            report["scenarios"][scenario]={"ticks":len(rows),"replay_equal":True,"sha256":digest,
                "air_ticks":sum(row["state"]=="1" for row in rows),
                "rail_ticks":sum(row["state"]=="4" for row in rows),
                "landings":sum(row["landed"]=="1" for row in rows)}
        if args.skeleton:
            if args.skeleton.stat().st_size>12+44*MAX_BONES:raise ValueError("Skeleton exceeds the supported THUG SKE v2 profile")
            rig=parse(args.skeleton.read_bytes())
            slug=re.sub(r"[^A-Za-z0-9_-]","_",args.skeleton.name)[:60] or "character"
            local=ROOT/"local-characters"/(slug+"-"+stamp+".rig.json")
            local.parent.mkdir(exist_ok=True)
            with local.open("x",encoding="utf-8") as file:json.dump(rig,file,indent=2,allow_nan=False);file.write("\n")
            report["character_rig"]={key:rig[key] for key in ("source_format","source_sha256","bone_count","source_flags","retail_validated")}
            report["character_rig"]["status"]="PARSED_LOCAL_RIG_ONLY"
            print("Local rig saved:",local,flush=True)
        report["passed"]=True
        print("PASS: embedded real THUG ground/air and rail ticks match the existing executable and replay.",flush=True)
    except Exception as error:
        status=1;report["passed"]=False;report["error"]=str(error);print(str(error),file=sys.stderr,flush=True)
    finally:
        report["exit_code"]=status
        (log/"report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        bundle=ROOT/"logs"/("GonkSkate-integration-results-"+stamp+".zip")
        # Explicit diagnostic whitelist: never export local rigs or game files.
        with zipfile.ZipFile(bundle,"w",zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(log.iterdir()):archive.write(path,path.name)
        print("Results ZIP:",bundle,flush=True)
    return status


if __name__=="__main__":sys.exit(main())
