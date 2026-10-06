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
        "RUN_CHARACTER_CHECK.cmd","scripts/run-character-check.py","tools/import_thug_skin.py",
        "tools/import_thug_character.py","tools/test_thug_character.py","tools/test_thug_rig.py",
        "tools/import_thug_animation.py","tools/test_thug_animation.py",
        "tools/import_thug_texture.py","tools/test_thug_texture.py",
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
        "validation/title-update-staging.json":(ROOT/"build/skate3-title-update-validation.json").read_bytes(),
        "validation/skin-loader.json":(ROOT/"build/skin-differential/validation.json").read_bytes(),
        "validation/character-preview.json":(ROOT/"build/character-preview-validation/validation.json").read_bytes(),
        "validation/animation-loader.json":(ROOT/"build/animation-differential/validation.json").read_bytes(),
        "validation/animation-preview.json":(ROOT/"build/animation-preview-validation/validation.json").read_bytes(),
        "validation/texture-loader.json":(ROOT/"build/texture-differential/validation.json").read_bytes(),
        "validation/texture-preview.json":(ROOT/"build/texture-preview-validation/validation.json").read_bytes()}
    if json.loads(evidence["validation/rig-loader.json"])["inverse_bind_equivalence"]!="PASS":raise ValueError("Rig differential check missing")
    if json.loads(evidence["validation/frontend-embedding.json"])["relocated_host_contracts"]!="PASS":raise ValueError("Frontend import check missing")
    for name in ("validation/skin-loader.json","validation/character-preview.json"):
        proof=json.loads(evidence[name])
        if proof.get("passed") is not True:raise ValueError("Character validation missing: "+name)
        expected={filename:hashlib.sha256((ROOT/"tools"/filename).read_bytes()).hexdigest()
            for filename in ("import_thug_rig.py","import_thug_skin.py","import_thug_character.py")}
        if proof.get("importer_source_sha256")!=expected:raise ValueError("Character evidence differs from packaged source: "+name)
    preview=json.loads(evidence["validation/character-preview.json"])
    if (preview.get("khronos_gltf_validator")!="PASS" or len(preview.get("fixtures",[]))!=4 or
        any(row.get("khronos_errors")!=0 or row.get("khronos_warnings")!=0 for row in preview["fixtures"])):
        raise ValueError("Independent character GLB validation is incomplete")
    for name, filenames in (("validation/animation-loader.json", ("import_thug_animation.py","import_thug_character.py","import_thug_rig.py")),
                            ("validation/animation-preview.json", ("import_thug_animation.py","import_thug_character.py","import_thug_rig.py","import_thug_skin.py"))):
        proof=json.loads(evidence[name])
        expected={filename:hashlib.sha256((ROOT/"tools"/filename).read_bytes()).hexdigest() for filename in filenames}
        if proof.get("passed") is not True or proof.get("importer_source_sha256")!=expected:
            raise ValueError("Animation evidence differs from packaged source: "+name)
    loader=json.loads(evidence["validation/animation-loader.json"])
    if (loader.get("original_platform_and_compressed_readers")!="PASS" or loader.get("original_pose_interpolation")!="PASS" or
        loader.get("original_skeleton_local_pose_math")!="PASS" or loader.get("bone_poses_compared",0)<8000):
        raise ValueError("Original animation differential validation is incomplete")
    animation=json.loads(evidence["validation/animation-preview.json"])
    if (animation.get("khronos_gltf_validator")!="PASS" or len(animation.get("fixtures",[]))!=5 or
        animation.get("engine_animation_bake_rate")!=60 or any(row.get("khronos_errors")!=0 or row.get("khronos_warnings")!=0 or
        row.get("actual_animation_playback")!="PASS" for row in animation["fixtures"])):
        raise ValueError("Independent animated playback validation is incomplete")
    texture_loader=json.loads(evidence["validation/texture-loader.json"])
    texture_hash={"import_thug_texture.py":hashlib.sha256((ROOT/"tools/import_thug_texture.py").read_bytes()).hexdigest()}
    if (texture_loader.get("passed") is not True or texture_loader.get("importer_source_sha256")!=texture_hash or
        texture_loader.get("original_unswizzle_equivalence")!="PASS" or texture_loader.get("source_stream_offsets_and_bytes")!="PASS"):
        raise ValueError("Original texture differential validation is incomplete")
    texture=json.loads(evidence["validation/texture-preview.json"])
    texture_sources={filename:hashlib.sha256((ROOT/"tools"/filename).read_bytes()).hexdigest()
        for filename in ("import_thug_texture.py","import_thug_character.py","import_thug_skin.py","import_thug_rig.py")}
    if (texture.get("passed") is not True or texture.get("importer_source_sha256")!=texture_sources or
        texture.get("khronos_gltf_validator")!="PASS" or len(texture.get("fixtures",[]))!=6 or
        any(row.get("khronos_errors")!=0 or row.get("khronos_warnings")!=0 or row.get("actual_texture_import")!="PASS" or
            row.get("material_texture_bound") is not True or row.get("maximum_channel_error")!=0 for row in texture["fixtures"])):
        raise ValueError("Independent textured preview validation is incomplete")
    for name, fixture in (("validation/character-preview.json","native/character_import/tests/preview_import.gd"),
                          ("validation/animation-preview.json","native/character_import/tests/animation_import.gd"),
                          ("validation/texture-preview.json","native/character_import/tests/texture_import.gd")):
        if json.loads(evidence[name]).get("engine_fixture_sha256")!=hashlib.sha256((ROOT/fixture).read_bytes()).hexdigest():
            raise ValueError("Engine fixture differs from playback evidence: "+fixture)
    readme=r'''# GonkSkate integration development check

Extract into a NEW folder. Run RUN_INTEGRATION_CHECK.cmd and return the
GonkSkate-integration-results ZIP under logs/. Python 3.10+ is required.
This is a console engine check, not a new playable release.

Real THUG ground/air/rail now runs from an embeddable DLL. The check verifies
native contracts and deterministic movement/replay against the prior executable.
No game files are needed. Keep the v0.8.0 playable package for workshop testing.

Optional local THUG skeleton:
RUN_INTEGRATION_CHECK.cmd "C:\\path\\to\\character.ske.xbx"
This command imports a rig only; use RUN_CHARACTER_CHECK.cmd for mesh previews.
The derived rig stays local; results contain diagnostics, not character assets.

NEW: run RUN_CHARACTER_CHECK.cmd for 26 asset-free rig/mesh/texture/animation/export checks.
For a matching local THUG PC skeleton and skin:
RUN_CHARACTER_CHECK.cmd "C:\\path\\to\\character.ske.xbx" "C:\\path\\to\\character.skin.xbx" --weight-profile dx9
Use --weight-profile xbox for the inspected original Xbox decoder instead.
This creates local-characters/thug-character-TIMESTAMP/character.glb and JSON.
The GLB is a rigged, untextured preview. Add a matching original texture dictionary:
RUN_CHARACTER_CHECK.cmd "C:\path\to\character.ske.xbx" "C:\path\to\character.skin.xbx" --weight-profile dx9 --textures "C:\path\to\character.tex.xbx"
This embeds the first source material pass. DXT1/DXT5 and swizzled 8/16/32-bit
images are supported; original multipass shader effects remain metadata.
Add a matching original skeletal clip:
RUN_CHARACTER_CHECK.cmd "C:\\path\\to\\character.ske.xbx" "C:\\path\\to\\character.skin.xbx" --weight-profile dx9 --animation "C:\\path\\to\\skater_Push.ska.xbx"
Select "THUG local clip" in your GLB viewer/editor's animation controls.
For compressed clips that require lookup tables, supply matching original local
--q-table and/or --t-table files (2048 bytes each). The importer reports missing
tables instead of guessing. It rejects unsupported partial/event/camera clips.
Bone counts must match; source files do not prove the correct rig identity.
Animation preview uses original samples at 60 Hz with STEP interpolation;
configure a viewer's animation resampling to retain 60 Hz if it bakes tracks.
This does not add a playable character. Retail texture compatibility, original
shader effects, gameplay animation selection and live attachment remain pending.
No game files are needed for the asset-free check.
Return the GonkSkate-character-results ZIP under logs/; derived assets stay local.

docs/THUG_EMBEDDED_RUNTIME.md contains the source-built Skate frontend helper.
That build needs local extracted Skate files, matching installed TU3 patches
(or a TU3 package) and the native build
toolchain. It links THUG into the frontend, but live player control remains pending.
docs/CHARACTER_IMPORT_PROGRESS.md explains the checked skeleton/mesh profiles.
'''
    info={"schema_version":1,"source_commit":revision,"scope":"integration development check",
        "entry_point":"RUN_INTEGRATION_CHECK.cmd","runtime_sha256":manifest["executable_sha256"],
        "validation":"Windows native host and MSVC-ABI host under Wine; owner Windows validation pending",
        "retail_assets_included":False,"live_skate_player_control":False,"complete_character_import":False,
        "character_check_entry_point":"RUN_CHARACTER_CHECK.cmd","rigged_neutral_character_preview":True,
        "original_clip_animated_character_preview":True,"character_preview_sample_rate":60,
        "original_texture_first_pass_preview":True,
        "sha256":{name:hashlib.sha256(data).hexdigest() for name,data in {**source,**binaries,**evidence}.items()}}
    with zipfile.ZipFile(output,"x",zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,data in {**source,**binaries,**evidence}.items():archive.writestr(prefix+name,data)
        archive.writestr(prefix+"README.md",readme)
        archive.writestr(prefix+"RELEASE_INFO.json",json.dumps(info,indent=2)+"\n")
    print(output);print("SHA256",hashlib.sha256(output.read_bytes()).hexdigest());print("Bytes",output.stat().st_size)


if __name__=="__main__":main()
