# Skate3Recomp presentation probe — development checkpoint

The next integration target is the real Skate frontend. This pass adds an
opt-in observer to ten existing upstream presentation wrappers, a bounded trace
recorder, a conservative analyzer, and a source-build staging tool. It does not
switch gameplay backends or write player state. The published v0.8.0 Windows
workshop package remains the owner test build.

## Verified source boundary

Inspected Skate3Recomp commit:
`f6e0ae87fdfecbadb5c1e36c55d66a744187a3cd`.
ReXGlue SDK: `7eb0faf7787f5e01333c228b8e3f03c32f7295ea`.
The source stager rejects changed pins or tracked modifications and leaves
the reference checkout intact. It archives only Git-tracked source into a new
ignored build directory. It copies no ISO, game dump, capture, generated guest
code, installed executable or saves.

| Existing wrapper | Observed event | Source evidence |
| --- | --- | --- |
| `82783D68` | Skater bind exit | SkaterPresEntity class tag; entity in r3 |
| `82785260` | Colorized bind exit | ColorizedSkaterPresEntity class tag; r3 |
| `82793F70` | CAC bind exit | CACPresEntity class tag; r3 |
| `82785528` | Auxiliary bind exit | Unnamed skater-layout class; r3 |
| `827825B0` | StartJobs entry/exit | Existing animation palette-owner bracket; r3 |
| `82782818` | EndJobs entry/exit | Existing animation palette-owner bracket; r3 |
| `82783038` | Garment buffer exit | Completed cloth output; r3 entity, r4 garment |
| `827A6C50` | View add entry | Presentation view registration; entity in r4 |
| `827A6CE8` | View removal entry | Presentation view removal; entity in r4 |
| `82B82E08` | Swap entry | Guest D3D presentation boundary |

These facts come from `src/skate3_native_render.cpp` and
`src/native/skate3_native_entity.cpp`. The observer captures argument registers
and incoming `ctx.lr` before calling the original import. It preserves that
import exactly once and retains the existing renderer and palette-owner order.

Pose samples read the entity's transposed Matrix44 at **+416**, following
upstream `ReadWorldRowsChecked`. Translation is in row elements **3, 7, 11**,
in meters. Every read goes through the upstream `GuestTryCopy` fault guard.
Two copies must agree; BE floats must be finite, the homogeneous tail valid,
and the row/translation bounds must match the upstream structural checks.
Faults, visible concurrent writes and invalid matrices become statuses.

The observed entities include NPCs and potentially replay/editor actors and
other presentation objects. An actor address is not a controlled-player symbol.
Animation and cloth jobs are not skating physics ticks. Swaps are not a fixed
simulation clock. Two equal snapshots do not prove an atomic game update.
Source addresses must still be verified against the locally generated game/TU3
configuration before drawing conclusions about a live run.

## Recorder and analysis contract

Recording is disabled unless `GONKSKATE_GUEST_PROBE_DIR` is set before launch.
Disabled hooks make no guest reads. On startup the observer creates a unique
JSONL file; an explicit exclusive descriptor open preserves existing files,
including on Windows runtimes that ignore fopen's `x` mode.

Guest callers perform guarded snapshots and a bounded try-lock enqueue. One
worker writes files. Defaults are a **4,096-event queue, 100,000-event limit and
32 MiB file limit**, including reserved summary space. Queue contention/overflow
drops observations and counts losses. Reaching a limit stops further snapshots.
Shutdown disables new calls, drains the writer, and retains the recorder until
the guest runtime has exited so an in-flight hook cannot access freed storage.
The observer catches initialization/writer failures and preserves normal game
execution. Hard process termination can leave a partial trace.

Each event includes sequence, host monotonic observation time, accepted-swap
epoch, thread tag, entity, hook, incoming caller address, pose status, optional
12 world floats, and garment detail. The stream order follows queue acceptance;
it does not reconstruct unsampled concurrent game writes. Time/thread tags are
observational and nondeterministic. A dropped swap also invalidates cadence
interpretation; accepted-swap epochs are not simulation frame numbers.

The analyzer checks schema, hook/kind agreement, finite matrix bounds, ordering,
footer counts, losses and limits. It reports per-actor pose changes, class tags,
observed path length and caller frequencies. Address reuse after observed view
removal starts another observed generation. That is view-membership evidence,
not a proven allocation lifetime. Teleports count toward observed path length.
It always leaves **player identity and simulation tick unresolved**. A partial,
limited or lossy stream produces an incomplete report and exit code **2**;
invalid/unsupported input produces **1**. A complete presentation report produces
**0**, which does not certify a physics boundary.

## Reproducible checks without retail data

```text
python tools/test_skate3_probe.py
cmake -S native/skate3_probe -B build/skate3-probe
cmake --build build/skate3-probe --parallel 2
ctest --test-dir build/skate3-probe --output-on-failure
```

The staging integration test runs when the pinned reference exists. Prepare its
headers with `python scripts/setup-skate3-source.py` first if needed.
`tools/build_skate3_probe.py` builds Linux or MinGW Windows fixtures in the
managed cloud toolchain (`GONK_CLANG` overrides the compiler). These use the
**actual SDK PPCContext and selected original wrapper bodies** with explicit
synthetic imports and guest-copy fixtures. They do not execute recompiled retail
code or validate the live renderer's guarded-copy machinery.

Validated in this pass:

- Ten wrapper bodies preserve original imports, complete PPC context, guest
  memory, palette ownership, and renderer callback ordering, enabled/disabled.
- Argument/caller capture survives original imports changing r3, r4 and LR.
- Unreadable/mutating/invalid snapshots, stopped/disabled hooks, concurrency,
  queue-loss accounting, event/byte limits and exclusive-file preservation.
- Native CMake library embedded in a synthetic host, including the production
  integration translation unit; standalone test targets stay disabled there.
- Linux contracts under address, undefined-behavior and thread sanitizers.
- Windows x64 contracts and wrapper execution under Wine; owner Windows
  execution of this development probe is pending.
- Seven Python tests covering NPC ambiguity, paused repeated poses, address
  reuse, partial/lost/limited streams, malformed poses and safe source staging.

The complete source-built Skate application has **not** been built or run here.
The cloud has no local retail dump/generated guest source. The synthetic host
test does not replace that validation.

## Source-build path for the next live checkpoint

This is a developer path, separate from the v0.8.0 workshop retest. It needs
the pinned upstream/SDK, all SDK submodules, upstream platform dependencies,
Clang and Ninja, and locally extracted game files plus the matching TU3 package.
On Windows use an x64 Native Tools shell with Clang 18+ (upstream recommends
20+) and CMake 3.25+. An installed release executable alone cannot accept these
source hooks. Read upstream README for graphics/toolchain requirements.

From the GonkSkate repository:

```powershell
python scripts/setup-skate3-source.py
git -C external/skate3 submodule update --init --recursive
python tools/stage_skate3_probe.py
Set-Location build/skate3-probe-source
# Review gonkskate-probe.patch and gonkskate-probe-manifest.json.
$gameDump = 'C:\path\to\extracted\Skate3\game'
$titleUpdate = 'C:\path\to\TU_12K2276_000000C000000.00000000000O3'
cmake --preset gonkskate-probe -DCMAKE_C_COMPILER=clang-cl -DCMAKE_CXX_COMPILER=clang-cl "-DSKATE3_GAME_DATA_ROOT=$gameDump" "-DSKATE3_TITLE_UPDATE_PACKAGE=$titleUpdate"
cmake --build --preset gonkskate-probe --target generate-all --parallel 2
cmake --preset gonkskate-probe -DCMAKE_C_COMPILER=clang-cl -DCMAKE_CXX_COMPILER=clang-cl "-DSKATE3_GAME_DATA_ROOT=$gameDump" "-DSKATE3_TITLE_UPDATE_PACKAGE=$titleUpdate"
cmake --build --preset gonkskate-probe --target skate3 --parallel 2
$env:GONKSKATE_GUEST_PROBE_DIR = Join-Path $PWD 'user\guest-probe'
& .\out\build\gonkskate-probe\skate3.exe "--game_data_root=$gameDump"
Remove-Item Env:GONKSKATE_GUEST_PROBE_DIR
```

Judge native commands by exit codes and stop on failure. A new staging directory
is required for another pass; existing output is intentionally never overwritten.
The generated user preset points to the original pinned SDK tree. The staged
CMake patch fixes upstream's hardcoded crypto path and stamps a distinct probe
version instead of inheriting GonkSkate's parent Git tags. Linux uses the
`gonkskate-probe-linux` preset and upstream Clang 20/platform dependencies.

Once it builds, first run without the environment variable to verify ordinary
Skate/controller behavior. Then take short separate recordings: idle, move one
controlled skater, ollie, grind, open/close the settings menu. Quit normally to
finish each trace; dense scenes can reach the cap before the test finishes.
Do not combine unrelated actions into a long limited trace.

Back at the GonkSkate repository, analyze a completed file:

```powershell
python tools/analyze_skate3_probe.py 'C:\path\to\skate3-presentation-TIMESTAMP.jsonl' --output 'logs\guest-probe-report.json'
```

The report path must be new and its parent folder must exist. Share the JSON
report and matching JSONL if requested; no ISO, game dump, raw memory, capture
geometry or generated guest source is needed for those diagnostics.

## Resume here

1. Keep v0.8.0 owner workshop/rail testing separate and incorporate its results.
2. Complete the full local source build and verify ordinary Skate/controller
   behavior before enabling observation.
3. Use actor/caller traces plus local generated-code inspection to establish
   controlled-player ownership. Do not select the most active actor as a shortcut.
4. Locate the actual simulation scheduler and demonstrate update behavior
   while idle, moving and paused; keep render and cloth cadence separate.
5. Find original collision ownership and the supported player state/control
   boundary. Only then attach THUG with explicit input/time/state ownership.
6. Prove one backend controls the skater, camera/presentation follow it, and
   both modes consume the same selected world. Presentation transform writes
   alone would not establish this combination.
