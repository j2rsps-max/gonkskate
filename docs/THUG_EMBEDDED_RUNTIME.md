# Embedded THUG runtime development checkpoint

Real THUG ground/air/rail physics now builds as a reusable Windows x64 DLL and
Linux shared library. The executable and library share one `Session` containing
the original skater/core/state/rotation code and the tested environmental profile.
This removes the subprocess requirement for a future Skate frontend attachment.

The staged Skate source can link this library and check its ABI during
`OnPostSetup()`. The full retail Skate app has not been built in the cloud, and
the library is not yet driving its controlled player. Original controller/gameplay
behavior remains the default. Player ownership, authoritative scheduling and
guest collision coupling still need the live probe described in
[SKATE3_GUEST_PROBE.md](SKATE3_GUEST_PROBE.md).

## Quick Windows check

Use the separate **Integration Check** development ZIP from GitHub. Extract it
into a new folder and run `RUN_INTEGRATION_CHECK.cmd`. Python 3.10+ is required;
it needs no Cargo, CMake, Visual Studio, ISO or game files for this check.
It opens a console and tests the engine library, rather than opening a game window.

The check tests ABI/thread/lifecycle contracts, then executes and replays the
original 360-tick ground/ollie/landing and rail scenarios. Both traces must match
the existing executable's recorded hashes. Return the single
`logs/GonkSkate-integration-results-TIMESTAMP.zip`, even if it fails.

Optionally check a locally supplied THUG skeleton at the same time:

```powershell
.\RUN_INTEGRATION_CHECK.cmd 'C:\path\to\character.ske.xbx'
```

Supported skeletons are restricted to the inspected v2 little-endian profile.
The rig stays in `local-characters/`; only its metadata enters the results ZIP.
This does not add a playable character. See [character progress](CHARACTER_IMPORT_PROGRESS.md).

The v0.8.0 full playable ZIP remains the workshop/controller test package.
Keep it while testing this separate development checkpoint.

## Runtime contract

Use `native/thug_adapter/include/gonkskate_thug_runtime.h`, ABI version 1.
This is the implemented lifecycle, distinct from the older design-only
declarations in `gonkskate_thug.h`.

- One live session per process, used and destroyed by its creator thread.
- `create` selects a synthetic floor, the original synthetic test area, or a
  UTF-8 normalized `.gonkworld` file. Inputs are copied/loaded during creation.
- `step` executes one 60 Hz tick with original pad pressures (0–255).
- Positions/velocities use inches and inches per second; basis vectors are
  returned for host presentation. `completed_ticks` counts successful ticks.
- Native state IDs remain THUG's: ground 0, air 1, wall 2, lip 3, rail 4,
  wallplant 5. They differ from the earlier provisional design enum.
- State includes terrain, rail, landing and per-tick query/lookup/dependency counts.
- Unsupported dependencies and mapped THUG assertions return status/error
  information instead of exiting the embedding application. A failed session
  rejects further stepping/state reads; destroy it and create another.
- Last error belongs to the calling thread. Copy successful state to the
  renderer rather than calling a creator-thread session from another thread.

Global environmental/timing facades are still present. Multi-player sessions,
variable timesteps, moving worlds, full balance/scoring, animations and bails
remain outside the tested profile. No guessed guest physics clock or player
transform writes are added by the source-stage handshake.

## Native validation

Linux and Windows under Wine pass ABI mismatch, malformed buffers, wrong-thread
access, duplicate sessions, stale handles, reset, destroy/recreate, and Unicode
world paths. Test-only libraries also exercise an actual unresolved manual call
and a collision ABI failure inside original `Update()`. The latter interrupts
cache cleanup; session teardown now clears the default feeler cache before
destroying the skater, and a recreated session completes the normal landing.
Production libraries exclude these fault-injection exports.

Idle, ollie, steer, 10,000-tick soak, rail and rail-jump traces are byte-identical
to the pre-extraction executable on Linux and Windows. The standalone executable
also passes its existing behavior suite, including ramp/IPC/reset checks.
Original gravity, stat interpolation and update order are preserved.

A freestanding Windows host compiled with Clang's **MSVC ABI** links the actual
GNU-built DLL/import library and executes 60 real ticks under Wine. This tests
the ABI used by Skate's frontend toolchain. The shared CMake import module is
also tested by linking and running a relocated Linux host with only its copied
executable/library. Neither fixture executes retail Skate guest code.

Cloud developer commands:

```bash
python3 tools/build_thug_headless.py --mode library
python3 tools/build_thug_headless.py --mode library --test-hooks
python3 tools/test_thug_runtime.py build/thug-runtime --baseline build/runtime-baseline/gonkskate-thug-test
python3 tools/test_thug_runtime.py build/thug-runtime-test --baseline build/runtime-baseline/gonkskate-thug-test
python3 tools/test_thug_embedding.py build/thug-runtime
python3 tools/build_thug_headless.py --target windows --mode library
```

Preserve an existing baseline executable before rebuilding; alternatively pass
an explicit baseline from a known working package. The build helper currently
uses the cloud Clang/MinGW toolchain, or `GONK_CLANG`/`GONK_MINGW` overrides.
Windows owners can use the prebuilt production DLL in the development ZIP.

## Build the Skate frontend on Windows

The development ZIP includes a helper that prepares pinned source/SDK dependencies,
stages a fresh source tree, configures, generates the guest, reconfigures and
builds. It verifies extracted TU3 payload hashes before generating the guest.
It records each exit code and exports log tails without retail files.
Existing tracked changes are preserved by stopping before submodule updates.
This full build workflow remains pending owner validation.

Use **x64 Native Tools Command Prompt for VS 2022** with LLVM/Clang (upstream
recommends 20+), CMake 3.25+, Ninja, Git and Python available. Supply the extracted
game directory, not the ISO. The helper reuses hash-verified installed TU3
patches when they are in that directory:

```powershell
python scripts/build-skate3-integration.py --game-root "C:\path\to\Skate3\game" --preflight-only
python scripts/build-skate3-integration.py --game-root "C:\path\to\Skate3\game"
```

The default is one compile job for a 16 GB PC. The helper prints the new
`skate3.exe` path after success and always produces an
`GonkSkate-integration-build-results-TIMESTAMP.zip`. Return that ZIP on failure.
It does not launch or replace the installed recompilation.

If the patches are elsewhere, add `--staged-tu-root "C:\path\to\patch-root"`.
If you only have a TU3 STFS package, add
`--title-update "C:\path\to\TU_12K2276_000000C000000.00000000000O3"` instead.
Both paths copy inputs into the private build tree; original files stay intact.
Synthetic CMake fixtures verify those copies, hash rejection, exclusive input
selection and the retained STFS branch. The fixed external-SDK crypto header and
implementation also compile and pass a standard SHA256 fixture.

For manual source staging from the repository:

```powershell
python tools/stage_skate3_probe.py --thug-runtime bin/thug-runtime --output build/skate3-integration-source
```

Review the generated patch and provenance manifest. CMake links the library and
copies the DLL beside the executable. A successful `OnPostSetup()` logs
`GonkSkate THUG runtime ABI 1 loaded; gameplay attachment pending`.
Then follow the guest-probe guide for ordinary-controller verification and short
presentation recordings. Establish player/tick/collision ownership before
attaching an authoritative THUG session.
