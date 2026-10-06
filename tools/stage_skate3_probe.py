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


def patch_app(text):
    for function, call in [("OnPostSetup", "Start"), ("OnShutdown", "Stop")]:
        marker = f"void Skate3BaseApp::{function}() {{"
        if text.count(marker) != 1:
            raise ValueError(f"Expected lifecycle hook: {function}")
        text = text.replace(marker, marker + f"\n  gonkskate::guest_probe::{call}();")
    return '#include "gonkskate_probe/integration/skate3_probe.h"\n' + text


def patch_cmake(text):
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
    return text + '''
# GonkSkate presentation observer. Runtime recording remains opt-in.
add_subdirectory(src/gonkskate_probe)
target_sources(skate3 PRIVATE src/gonkskate_probe/integration/skate3_probe.cpp)
target_link_libraries(skate3 PRIVATE gonkskate_skate3_probe)
'''


def stage(source, destination):
    source, destination = source.resolve(), destination.resolve()
    sdk = source / "third_party/rexglue-sdk"
    if destination.exists() or destination == source or source in destination.parents:
        raise ValueError("Choose a new staging directory outside the upstream checkout")
    for label, path, expected in [("Skate3Recomp", source, SKATE_PIN), ("SDK", sdk, SDK_PIN)]:
        if git(path, "rev-parse", "HEAD").decode().strip() != expected:
            raise ValueError(f"{label} differs from inspected source pin")
        if git(path, "status", "--porcelain", "--untracked-files=no").strip():
            raise ValueError(f"{label} has tracked changes; preserve/reconcile them before staging")
    originals = {name: git(source, "show", f"HEAD:{name}").decode()
                 for name in ["src/skate3_native_render.cpp", "src/skate3_app_common.cpp", "CMakeLists.txt"]}
    patched = {"src/skate3_native_render.cpp": patch_render(originals["src/skate3_native_render.cpp"]),
               "src/skate3_app_common.cpp": patch_app(originals["src/skate3_app_common.cpp"]),
               "CMakeLists.txt": patch_cmake(originals["CMakeLists.txt"])}
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
            manifest = {"schema_version": 1, "skate3_commit": SKATE_PIN, "sdk_commit": SDK_PIN,
                "scope": "presentation-only", "player_identity": "unresolved", "simulation_tick": "unresolved",
                "retail_code_executed": False, "hooks": HOOKS,
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
    args = parser.parse_args()
    try:
        path = stage(args.source, args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Staging failed: {error}\n")
    print(f"Staged source: {path}\nReview: {path / 'gonkskate-probe.patch'}")
    print("Build and recording instructions: docs/SKATE3_GUEST_PROBE.md")


if __name__ == "__main__":
    main()
