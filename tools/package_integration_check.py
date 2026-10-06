"""Package the validated Windows production runtime and source-stage tooling.

Explicit code/diagnostic whitelist: no retail files, captures, local rigs,
generated guest code, test-hook library, installed game or Godot is included.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from stage_skate3_probe import ROOT, runtime_files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime",type=Path,default=ROOT/"build/thug-runtime-windows")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    folder=args.runtime.resolve();manifest,_=runtime_files(folder)
    if manifest["target"]!="windows":parser.error("The download requires the Windows production runtime")
    validation=json.loads((folder/"runtime-validation.json").read_text())
    client=folder/"runtime-client.exe"
    if (validation.get("library_sha256")!=manifest["executable_sha256"] or validation.get("client_sha256")!=hashlib.sha256(client.read_bytes()).hexdigest() or
        validation.get("native_contracts")!="PASS" or validation.get("msvc_abi_host")!="PASS" or validation.get("test_hooks") is not False or
        set(validation.get("executable_equivalence",{}))!={"idle","ollie","steer","soak","rail","rail_jump"}):
        raise ValueError("Production runtime validation/provenance is incomplete")
    files=["RUN_INTEGRATION_CHECK.cmd","scripts/run-integration-check.py","scripts/build-skate3-integration.py",
        "scripts/setup-skate3-source.py","tools/import_thug_rig.py","tools/stage_skate3_probe.py","tools/skate3_readiness.py",
        "native/thug_adapter/include/gonkskate_thug.h","native/thug_adapter/include/gonkskate_thug_runtime.h",
        "native/thug_adapter/integration/SkateThugRuntime.cmake","native/skate3_adapter/config/upstream.json",
        "docs/THUG_EMBEDDED_RUNTIME.md","docs/CHARACTER_IMPORT_PROGRESS.md","docs/SKATE3_GUEST_PROBE.md","VERSION"]
    files += subprocess.check_output(["git","ls-files","native/skate3_probe"],cwd=ROOT,text=True).splitlines()
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    # Ship committed source so the named revision is an accurate provenance claim.
    source={name:subprocess.check_output(["git","show",f"HEAD:{name}"],cwd=ROOT) for name in files}
    for name,data in source.items():
        if data!=(ROOT/name).read_bytes():raise ValueError("Commit the final source before packaging: "+name)
    prefix=f"GonkSkate-Integration-Check-{revision[:7]}/"
    output=args.output or ROOT.parent/f"GonkSkate-Integration-Check-{revision[:7]}.zip"
    if output.exists():raise ValueError("Choose a new output ZIP; existing downloads are preserved")
    binaries={"bin/thug-runtime/"+name:(folder/name).read_bytes() for name in (
        "gonkskate-thug-runtime.dll","gonkskate-thug-runtime.lib","runtime-client.exe","manifest.json","runtime-validation.json")}
    evidence={"validation/rig-loader.json":(ROOT/"build/rig-differential/validation.json").read_bytes(),
        "validation/frontend-embedding.json":(ROOT/"build/thug-runtime/frontend-embedding-validation.json").read_bytes(),
        "validation/title-update-staging.json":(ROOT/"build/skate3-title-update-validation.json").read_bytes()}
    if json.loads(evidence["validation/rig-loader.json"])["inverse_bind_equivalence"]!="PASS":raise ValueError("Rig differential check missing")
    if json.loads(evidence["validation/frontend-embedding.json"])["relocated_host_contracts"]!="PASS":raise ValueError("Frontend import check missing")
    readme='''# GonkSkate integration development check

Extract into a NEW folder. Run RUN_INTEGRATION_CHECK.cmd and return the
GonkSkate-integration-results ZIP under logs/. Python 3.10+ is required.
This is a console engine check, not a new playable release.

Real THUG ground/air/rail now runs from an embeddable DLL. The check verifies
native contracts and deterministic movement/replay against the prior executable.
No game files are needed. Keep the v0.8.0 playable package for workshop testing.

Optional local THUG skeleton:
RUN_INTEGRATION_CHECK.cmd "C:\\path\\to\\character.ske.xbx"
This imports a rig only. Meshes/animations/playable characters remain pending.
The derived rig stays local; results contain diagnostics, not character assets.

docs/THUG_EMBEDDED_RUNTIME.md contains the source-built Skate frontend helper.
That build needs local extracted Skate files, matching installed TU3 patches
(or a TU3 package) and the native build
toolchain. It links THUG into the frontend, but live player control remains pending.
docs/CHARACTER_IMPORT_PROGRESS.md explains the verified skeleton profile.
'''
    info={"schema_version":1,"source_commit":revision,"scope":"integration development check",
        "entry_point":"RUN_INTEGRATION_CHECK.cmd","runtime_sha256":manifest["executable_sha256"],
        "validation":"Windows native host and MSVC-ABI host under Wine; owner Windows validation pending",
        "retail_assets_included":False,"live_skate_player_control":False,"complete_character_import":False,
        "sha256":{name:hashlib.sha256(data).hexdigest() for name,data in {**source,**binaries,**evidence}.items()}}
    with zipfile.ZipFile(output,"x",zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,data in {**source,**binaries,**evidence}.items():archive.writestr(prefix+name,data)
        archive.writestr(prefix+"README.md",readme)
        archive.writestr(prefix+"RELEASE_INFO.json",json.dumps(info,indent=2)+"\n")
    print(output);print("SHA256",hashlib.sha256(output.read_bytes()).hexdigest());print("Bytes",output.stat().st_size)


if __name__=="__main__":main()
