"""Stage a reviewable, pinned Skate3Recomp source build with read-only hooks.

Copies only Git-tracked upstream source. No worktree, generated retail code,
ISO, memory capture, game folder or installed executable is copied or modified.
"""
import argparse
import difflib
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKATE_PIN = "f6e0ae87fdfecbadb5c1e36c55d66a744187a3cd"
SDK_PIN = "7eb0faf7787f5e01333c228b8e3f03c32f7295ea"
THUG_PIN = "98b4e24921446ccd4b157453e25697f9574f0053"
# Address, argument register, entry marker, exit marker. These are existing
# upstream presentation wrappers, not inferred authoritative simulation hooks.
HOOKS = {
    "82B82E08": (None, "swap_begin", None),
    "827825B0": (3, "jobs_start_enter", "jobs_start_exit"),
    "82782818": (3, "jobs_end_enter", "jobs_end_exit"),
    "82783038": (3, None, "garment_exit"),
    "827A6C50": (4, "view_add", None),
    "827A6CE8": (4, "view_remove", None),
    "82783D68": (3, None, "bind_skater"),
    "82785260": (3, None, "bind_colorized"),
    "82793F70": (3, None, "bind_cac"),
    "82785528": (3, None, "bind_aux"),
}


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args])


def function_span(text, address):
    marker = f'extern "C" REX_FUNC(sub_{address})'
    if text.count(marker) != 1:
        raise ValueError(f"Expected exactly one existing wrapper: {address}")
    start = text.index(marker)
    opening = text.index("{", start)
    depth = 1
    end = opening + 1
    while depth and end < len(text):
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    if depth:
        raise ValueError("Unbalanced upstream wrapper")
    return start, opening, end


def patch_render(text):
    for address, (register, before, after) in HOOKS.items():
        start, opening, end = function_span(text, address)
        body = text[opening + 1:end - 1]
        original = f"  __imp__sub_{address}(ctx, base);"
        if body.count(original) != 1:
            raise ValueError(f"Expected one original call: {address}")
        entity = f"ctx.r{register}.u32" if register else "0"
        prefix = (f"\n  const uint32_t gonk_entity = {entity};\n"
                  "  const uint32_t gonk_caller = static_cast<uint32_t>(ctx.lr);\n")
        if address == "82783038":
            prefix += "  const uint32_t gonk_detail = ctx.r4.u32;\n"

        def observe(kind):
            detail = ", gonk_detail" if address == "82783038" else ""
            return ("  gonkskate::guest_probe::Observe(base, gonk_entity, "
                    f"gonkskate::probe::Kind::{kind}, 0x{address}, gonk_caller{detail});\n")

        if before:
            prefix += observe(before)
        if after:
            # Post marker after original returns, before existing observation.
            body = body.replace(original, original + "\n" + observe(after).rstrip())
        body = prefix + body
        text = text[:opening + 1] + body + text[end - 1:]
    return '#include "gonkskate_probe/integration/skate3_probe.h"\n' + text


def patch_app(text, embedded=False):
    for function, call in [("OnPostSetup", "Start"), ("OnShutdown", "Stop")]:
        marker = f"void Skate3BaseApp::{function}() {{"
        if text.count(marker) != 1:
            raise ValueError(f"Expected lifecycle hook: {function}")
        text = text.replace(marker, marker + f"\n  gonkskate::guest_probe::{call}();")
    if embedded:
        # Load/link handshake only. No guessed physics cadence or guest writes.
        marker = "void Skate3BaseApp::OnPostSetup() {"
        text = text.replace(marker, marker + '''
  const auto thug_abi = gonk_thug_runtime_abi_version();
  if (thug_abi != GONK_THUG_RUNTIME_ABI)
    throw std::runtime_error("GonkSkate THUG runtime ABI mismatch");
  REXLOG_INFO("GonkSkate THUG runtime ABI {} loaded; gameplay attachment pending", thug_abi);''')
        text = '#include <gonkskate_thug_runtime.h>\n#include <stdexcept>\n' + text
    return '#include "gonkskate_probe/integration/skate3_probe.h"\n' + text


def patch_cmake(text, embedded=False):
    version = '''skate3_resolve_version(SKATE3_FULL_VERSION
    FLOOR_VERSION ${PROJECT_VERSION}
    SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR})'''
    if text.count(version) != 1:
        raise ValueError("Expected upstream version resolver")
    # An archive under GonkSkate's build/ would otherwise inherit the parent
    # repository's tags. Stamp the inspected upstream identity explicitly.
    text = text.replace(version, f'set(SKATE3_FULL_VERSION "2.0.0-gonkskate-probe.{SKATE_PIN[:8]}")')
    crypto = "    third_party/rexglue-sdk/thirdparty/crypto/sha256.cpp"
    if text.count(crypto) != 1:
        raise ValueError("Expected upstream SDK crypto source")
    text = text.replace(crypto, '    "${REXSDK_DIR}/thirdparty/crypto/sha256.cpp"')
    condition = 'if(NOT SKATE3_EFFECTIVE_TITLE_UPDATE_PACKAGE STREQUAL "")'
    if text.count(condition) != 3:
        raise ValueError("Expected three upstream title-update activation conditions")
    text = text.replace(condition, 'if(NOT SKATE3_EFFECTIVE_TITLE_UPDATE_PACKAGE STREQUAL "" OR NOT GONKSKATE_STAGED_TU_ROOT STREQUAL "")')
    marker = 'set(SKATE3_PATCHED_DEFAULT_XEX_LINE "")'
    settings = '''set(GONKSKATE_STAGED_TU_ROOT "" CACHE PATH "Existing local TU3 patch root; inputs stay untouched")
if(NOT GONKSKATE_STAGED_TU_ROOT STREQUAL "" AND NOT SKATE3_EFFECTIVE_TITLE_UPDATE_PACKAGE STREQUAL "")
    message(FATAL_ERROR "Choose installed TU3 patches or an STFS package, not both")
endif()
'''
    text = text.replace(marker, settings + marker, 1)
    text = text.replace('if(NOT EXISTS "${SKATE3_EFFECTIVE_TITLE_UPDATE_PACKAGE}")',
        'if(GONKSKATE_STAGED_TU_ROOT STREQUAL "" AND NOT EXISTS "${SKATE3_EFFECTIVE_TITLE_UPDATE_PACKAGE}")', 1)
    start = text.index('    add_custom_command(\n        OUTPUT\n            "${SKATE3_TITLE_UPDATE_DEFAULT_XEX}"')
    end = text.index('    add_custom_target(skate3-title-update-codegen-inputs', start)
    original = text[start:end]
    pin = json.loads((ROOT / "native/skate3_adapter/config/upstream.json").read_text())
    hashes = {item["path"]: item["sha256"] for item in pin["title_update_payloads"]}
    installed = '''    if(NOT GONKSKATE_STAGED_TU_ROOT STREQUAL "")
        include(src/gonkskate_probe/integration/SkateTitleUpdate.cmake)
        gonkskate_stage_installed_tu("${SKATE3_GAME_DATA_ROOT}" "${GONKSKATE_STAGED_TU_ROOT}"
            "${SKATE3_TITLE_UPDATE_CODEGEN_ROOT}"
            "''' + hashes["default.xexp"] + '''"
            "''' + hashes["data/webkit/EAWebkit.xexp"] + '''")
    else()
''' + original + '''    endif()

'''
    text = text[:start] + installed + text[end:]
    text += '''
# GonkSkate presentation observer. Runtime recording remains opt-in.
add_subdirectory(src/gonkskate_probe)
target_sources(skate3 PRIVATE src/gonkskate_probe/integration/skate3_probe.cpp)
target_link_libraries(skate3 PRIVATE gonkskate_skate3_probe)
target_include_directories(skate3 PRIVATE "${REXSDK_DIR}/thirdparty/crypto")
'''
    if embedded:
        text += '''
# Real THUG runtime loaded in the Skate frontend; gameplay ownership pending.
include(src/gonkskate_thug_runtime/SkateThugRuntime.cmake)
gonkskate_embed_thug(skate3 "${CMAKE_CURRENT_SOURCE_DIR}/src/gonkskate_thug_runtime")
'''
    return text


def runtime_files(folder):
    """Whitelist and verify production binaries/headers before copying anything."""
    folder = folder.resolve()
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if (manifest.get("mode") != "library" or manifest.get("test_hooks") is not False or
        manifest.get("runtime_abi_version") != 1 or manifest.get("tick_hz") != 60 or
        manifest.get("upstream_commit") != THUG_PIN or manifest.get("target") not in ("linux", "windows")):
        raise ValueError("Expected a pinned production THUG runtime ABI 1 (test hooks forbidden)")
    windows = manifest["target"] == "windows"
    binary = "gonkskate-thug-runtime.dll" if windows else "libgonkskate-thug-runtime.so"
    files = {binary: (folder / binary, manifest.get("executable_sha256"))}
    if windows:
        files["gonkskate-thug-runtime.lib"] = (folder / "gonkskate-thug-runtime.lib", manifest.get("import_library_sha256"))
    for header in ("gonkskate_thug_runtime.h", "gonkskate_thug.h"):
        key = "native/thug_adapter/include/" + header
        files["include/" + header] = (ROOT / key, manifest.get("adapter_source_sha256", {}).get(key))
    if files["include/gonkskate_thug_runtime.h"][1] != manifest.get("abi_header_sha256"):
        raise ValueError("Runtime header provenance differs")
    for name, (path, expected) in files.items():
        if not expected or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Runtime provenance/hash mismatch: {name}")
    files["manifest.json"] = (manifest_path, hashlib.sha256(manifest_path.read_bytes()).hexdigest())
    cmake = ROOT / "native/thug_adapter/integration/SkateThugRuntime.cmake"
    files[cmake.name] = (cmake, hashlib.sha256(cmake.read_bytes()).hexdigest())
    return manifest, files


def stage(source, destination, runtime=None):
    source, destination = source.resolve(), destination.resolve()
    sdk = source / "third_party/rexglue-sdk"
    if destination.exists() or destination == source or source in destination.parents:
        raise ValueError("Choose a new staging directory outside the upstream checkout")
    for label, path, expected in [("Skate3Recomp", source, SKATE_PIN), ("SDK", sdk, SDK_PIN)]:
        if git(path, "rev-parse", "HEAD").decode().strip() != expected:
            raise ValueError(f"{label} differs from inspected source pin")
        if git(path, "status", "--porcelain", "--untracked-files=no").strip():
            raise ValueError(f"{label} has tracked changes; preserve/reconcile them before staging")
    embedded, runtime_copy = runtime_files(runtime) if runtime is not None else (None, {})
    originals = {name: git(source, "show", f"HEAD:{name}").decode()
                 for name in ["src/skate3_native_render.cpp", "src/skate3_app_common.cpp", "src/skate3_title_update_installer.cpp", "CMakeLists.txt"]}
    crypto_header = '#include "third_party/rexglue-sdk/thirdparty/crypto/sha256.h"'
    if originals["src/skate3_title_update_installer.cpp"].count(crypto_header) != 1:
        raise ValueError("Expected the pinned SDK crypto header include")
    patched = {"src/skate3_native_render.cpp": patch_render(originals["src/skate3_native_render.cpp"]),
               "src/skate3_app_common.cpp": patch_app(originals["src/skate3_app_common.cpp"], embedded is not None),
               "src/skate3_title_update_installer.cpp": originals["src/skate3_title_update_installer.cpp"].replace(crypto_header, '#include <sha256.h>'),
               "CMakeLists.txt": patch_cmake(originals["CMakeLists.txt"], embedded is not None)}
    archive = git(source, "archive", "HEAD")
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        members = tar.getmembers()
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError(f"Unsafe/non-source archive entry: {member.name}")
        destination.mkdir(parents=True)
        try:
            for member in members:
                target = destination / member.name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(tar.extractfile(member).read())
                    target.chmod(member.mode & 0o777)
            for name, text in patched.items():
                (destination / name).write_text(text, encoding="utf-8", newline="\n")
            probe_source = ROOT / "native/skate3_probe"
            shutil.copytree(probe_source, destination / "src/gonkskate_probe",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for name, (path, expected) in runtime_copy.items():
                target = destination / "src/gonkskate_thug_runtime" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                # Recheck bytes while copying rather than trusting a mutable source.
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError(f"Runtime changed during staging: {name}")
                target.write_bytes(data)
            # Separate development preset inherits the tested upstream toolchain.
            presets = {"version": 6, "configurePresets": [], "buildPresets": []}
            for name, parent in [("gonkskate-probe", "relwithdebinfo"),
                                 ("gonkskate-probe-linux", "linux-relwithdebinfo")]:
                presets["configurePresets"].append({"name": name, "inherits": parent,
                    "cacheVariables": {"REXSDK_DIR": sdk.as_posix()}})
                presets["buildPresets"].append({"name": name, "configurePreset": name})
            (destination / "CMakeUserPresets.json").write_text(json.dumps(presets, indent=2)+"\n")
            diff = "".join("".join(difflib.unified_diff(originals[name].splitlines(True),
                patched[name].splitlines(True), fromfile=f"a/{name}", tofile=f"b/{name}")) for name in originals)
            (destination / "gonkskate-probe.patch").write_text(diff, encoding="utf-8", newline="\n")
            tracked = [destination / name for name in patched]
            tracked += sorted((destination / "src/gonkskate_probe").rglob("*"))
            tracked += sorted((destination / "src/gonkskate_thug_runtime").rglob("*"))
            manifest = {"schema_version": 1, "skate3_commit": SKATE_PIN, "sdk_commit": SDK_PIN,
                "scope": "presentation-only", "player_identity": "unresolved", "simulation_tick": "unresolved",
                "retail_code_executed": False, "hooks": HOOKS,
                "thug_runtime": ({"abi_version": 1, "target": embedded["target"],
                    "upstream_commit": THUG_PIN, "binary_sha256": embedded["executable_sha256"],
                    "gameplay_attached": False} if embedded is not None else None),
                "original_sha256": {name: hashlib.sha256(text.encode()).hexdigest() for name, text in originals.items()},
                "staged_sha256": {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in tracked if p.is_file()}}
            (destination / "gonkskate-probe-manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
        except BaseException:
            shutil.rmtree(destination)
            raise
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "external/skate3")
    parser.add_argument("--output", type=Path, default=ROOT / "build/skate3-probe-source")
    parser.add_argument("--thug-runtime", type=Path, help="Optional production library build directory; links THUG into the frontend")
    args = parser.parse_args()
    try:
        path = stage(args.source, args.output, args.thug_runtime)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Staging failed: {error}\n")
    print(f"Staged source: {path}\nReview: {path / 'gonkskate-probe.patch'}")
    print("Build and recording instructions: docs/SKATE3_GUEST_PROBE.md")


if __name__ == "__main__":
    main()
