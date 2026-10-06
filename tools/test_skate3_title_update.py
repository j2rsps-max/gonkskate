"""Exercise actual staged CMake title-update logic using synthetic local files.

Only the two expected hash constants are substituted for synthetic fixture
hashes. Production staging keeps the inspected TU3 values. No retail codegen.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from stage_skate3_probe import ROOT, stage


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cmake",default="cmake")
    parser.add_argument("--cxx",default="c++")
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(dir=ROOT/"build") as temporary:
        folder=Path(temporary);staged=stage(ROOT/"external/skate3",folder/"source")
        cmake=(staged/"CMakeLists.txt").read_text()
        block=cmake[cmake.index('set(SKATE3_EFFECTIVE_TITLE_UPDATE_PACKAGE'):cmake.index('file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/manifests")')]
        hashes={row["path"]:row["sha256"] for row in json.loads((ROOT/"native/skate3_adapter/config/upstream.json").read_text())["title_update_payloads"]}
        game=folder/"local game";game.mkdir()
        originals={"default.xex":b"synthetic original xex", "data/webkit/EAWebkit.xex":b"synthetic webkit xex",
            "default.xexp":b"synthetic default patch", "data/webkit/EAWebkit.xexp":b"synthetic webkit patch"}
        for name,data in originals.items():
            path=game/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        for name,expected in hashes.items():block=block.replace(expected,hashlib.sha256(originals[name]).hexdigest())
        # Use the real staged CMake branch and its actual module, with only
        # synthetic payload hash constants replacing the retail pin values.
        (staged/"CMakeLists.txt").write_text('''cmake_minimum_required(VERSION 3.25)
project(title_update_fixture LANGUAGES NONE)
set(SKATE3_SOURCE_DIR_CONFIG "${CMAKE_CURRENT_SOURCE_DIR}")
'''+block)
        def configure(output,patch_root=None,package=None):
            command=[args.cmake,"-S",str(staged),"-B",str(output),"-DSKATE3_GAME_DATA_ROOT="+str(game)]
            if patch_root:command+=["-DGONKSKATE_STAGED_TU_ROOT="+str(patch_root)]
            if package:command+=["-DSKATE3_TITLE_UPDATE_PACKAGE="+str(package)]
            return subprocess.run(command,capture_output=True,text=True)
        build=folder/"out";result=configure(build,game);assert result.returncode==0,result.stderr
        subprocess.run([args.cmake,"--build",str(build),"--target","skate3-title-update-codegen-inputs"],check=True)
        for name,data in originals.items():
            assert (game/name).read_bytes()==data,"Original local input changed"
            assert (build/"title_update_codegen"/name).read_bytes()==data,"Private staged bytes differ"
        # Codegen may operate on its private XEX copy without altering the game.
        (build/"title_update_codegen/default.xex").write_bytes(b"private mutation")
        assert (game/"default.xex").read_bytes()==originals["default.xex"]
        (game/"default.xexp").write_bytes(b"wrong title update")
        result=configure(folder/"wrong-hash",game)
        assert result.returncode!=0 and "patch hash differs" in result.stderr
        (game/"default.xexp").write_bytes(originals["default.xexp"])
        package=folder/"local package.stfs";package.write_bytes(b"LIVEsynthetic")
        result=configure(folder/"ambiguous",game,package)
        assert result.returncode!=0 and "not both" in result.stderr
        # The original package branch still configures without selecting local patches.
        result=configure(folder/"package",package=package);assert result.returncode==0,result.stderr
        sdk=ROOT/"external/skate3/third_party/rexglue-sdk"
        fixed=(staged/"src/skate3_title_update_installer.cpp").read_text()
        assert '#include <sha256.h>' in fixed and 'third_party/rexglue-sdk/thirdparty/crypto/sha256.h' not in fixed
        source=folder/"crypto.cpp"
        source.write_text('#include <sha256.h>\nint main(){sha256::SHA256 hash;return hash("abc")!="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";}\n')
        exe=folder/"crypto"
        subprocess.run([args.cxx,"-std=c++17","-I"+str(sdk/"thirdparty/crypto"),str(source),str(sdk/"thirdparty/crypto/sha256.cpp"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    report={"passed":True,"installed_patch_staging":"PASS","original_inputs_preserved":True,
        "wrong_hash_and_ambiguous_inputs_rejected":True,"original_package_branch_configures":True,
        "external_sdk_crypto_header_and_source":"PASS","retail_assets_used":False,"retail_codegen_run":False}
    (ROOT/"build/skate3-title-update-validation.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
