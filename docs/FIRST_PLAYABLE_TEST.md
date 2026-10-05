# v0.6.0: first THUG flat-floor playable preview

The standalone runtime compiles the whole upstream
`Obj::CSkaterCorePhysicsComponent` and calls its normal `Update()` at 60 Hz.
Original state, rotation, math, pad/button and base-component code is also compiled.
The Rust host and its two prototype backends remain available; this preview uses
an isolated native process to get an interactive proof before linking the whole
runtime into the Rust backend. Godot handles input, the camera and presentation.
Godot does not simulate the skater's motion.

## Run on Windows

Extract **GonkSkate-v0.6.0-Windows-Playable-Full-Package.zip** into a writable
folder. The package includes the x64 native executable and Godot 4.4.1; Python 3
is the only launcher prerequisite. Run:

```powershell
.\RUN_PLAYABLE.cmd
```

Controls:

| Action | Keyboard | Controller |
| --- | --- | --- |
| Push | W or Up | Left face button (Xbox X) |
| Steer | A/D or Left/Right | Left stick left/right |
| Brake | S or Down | Left stick down |
| Crouch/ollie | Hold Space, release to ollie | Hold bottom face button, release |
| Quit | Escape | Keyboard Escape |

Stick input is currently converted to digital directions. Analog-strength input,
tricks, grinds, bails, audio and animation are not part of this preview. The
placeholder skater is built from procedural shapes. The floor is an infinite,
two-sided y=0 plane with an upward normal and smooth-concrete terrain. The drawn
grid is a visual reference, with no obstacles or rails.

For a hands-free six-second scene integration check:

```powershell
.\RUN_PLAYABLE.cmd --autotest
```

Both commands first verify the native runtime, then save the scene output,
per-frame CSV trace and peripheral-call report in
`logs\GonkSkate-playable-results-*.zip`. Return that ZIP after trying movement,
turns and repeated ollies. Windows hardware input and rendering still need the
owner's actual-machine test; Wine validation does not replace it.

`RUN_FIRST_TEST.cmd` remains the older Rust/ABI readiness harness and preserves
its PowerShell 5.1 stderr fixes. `RUN_PLAYABLE.cmd` launches the authentic test.

## What has been verified

- Idle holds the spawn point; square/push produces real ground acceleration.
- Fifteen crouched frames build tense time. Releasing ollie at frame 165 emits
  the original `Ollied` event. The flat-floor event handler issues the public
  `Jump` command, which runs original `do_jump()`; no upward velocity is invented.
- Original air physics applies -1350 inches/s² gravity. The apex is approximately
  63.2 inches; landing at frame 203 sets `landed_this_frame` once.
- Steering changes heading and movement; braking stops the skater.
- 10,000 fixed ticks complete 55 ollies/landings without unexpected dependencies.
- Replays are byte-identical; live input over the process pipe reproduces the
  scripted trace. Invalid input fails with an exit code and diagnostic.
- Reaching an unimplemented peripheral symbol prints its function and frame and
  exits nonzero. A deliberate manual-physics probe checks this path.
- Linux native/scene checks pass. The Windows x64 native suite and Godot 4.4.1
  scene integration check pass under Wine.
- Linux X11 keyboard-event injection verifies W, steering, braking, crouch/release,
  landing and Escape shutdown through the real interactive input path. The recorded
  session replays byte-identically in the native executable.
- The full Rust workspace, C++ ABI, stat differential (20,000 cases), parser and
  prototype backend-swap checks continue to pass.

These are standalone profile checks, not a matched original-game comparison
trace or proof that the whole THUG gameplay system has been ported.

## Environment adaptation and limits

Upstream pin: `98b4e24921446ccd4b157453e25697f9574f0053`.
Generated source lives only under ignored `build/`. The reference checkout is
never rewritten. Build manifests record source/executable hashes and every
fail-fast peripheral symbol.

`prepare_thug_headless.py` normalizes case/separators in includes and adapts
legacy template/debug syntax, platform types, allocator queries and math-header
portability. It replaces the rendered skater wrapper and four global-service
headers with small headless facades. It preserves the core Update/state physics
algorithms, math, state component and rotation component.

The component list preserves the relevant original construction order. The
headless frame boundary stores `m_old_pos` after core/rotate, matching the final
assignment in `SkaterAdjustPhysicsComponent::Update()`. Renderer-dependent
adjustments are omitted for the plane. Allocation keeps the original
`ZERO_CLASS_MEM` convention. Both `Tmr::FrameLength()` and `GetTime()` derive from
the same frame counter; integer milliseconds match THUG's timer API.

Input uses original button edge/timing code. The event facade supports Ollied
and Landed; the original script VM, animation and scoring scripts are absent.
Sound, score spin accounting, cheats, network, park queries, static collision
caching, triggers and moving contacts have explicit instrumented behavior.
Other linked dependencies fail fast. This is not a complete substitute for their
behavior on imported worlds.

`gonkskate_thug_collision.h` adds version 2 collision query/hit structures with
segment fraction, ignore masks, nearest/farthest intent, flags, terrain,
trigger/script/node and moving metadata. CFeeler uses this callback seam;
`thug_flat_world.cpp` implements the plane. The old illustrative Rust world ABI
is retained and is not the authoritative collision bridge for this executable.
Moving/trigger/script hits are rejected by this profile. Rail/sector queries are
still unsupported. THUG's internal state values in CSV are documented by the
upstream enum; the public C ABI enum needs explicit mapping when runtime handles
are integrated. Existing `gonk_thug_create/step` declarations are still a future
library interface, not implemented symbols in this executable.

## Build and reproduce on Linux

On this Debian cloud image, `bash scripts/setup-cloud.sh` prepares pinned Rust,
CMake and locally extracted Clang using signed Debian package indexes, preserves
an existing upstream checkout, and runs native, Rust and scene checks.

```bash
export RUSTUP_HOME=/workspace/tooling/rustup
export CARGO_HOME=/workspace/tooling/cargo
export PATH=/workspace/tooling/cargo/bin:/workspace/tooling/python/bin:$PATH
python3 scripts/test-all.py
python3 scripts/run-playable.py --autotest
# With a desktop/display available:
python3 scripts/run-playable.py
```

Rebuild the Windows binary from Linux:

```bash
python3 scripts/setup-native-tools.py --windows
python3 tools/build_thug_headless.py --target windows
```

Windows source compilation with Visual Studio is not implemented yet. The
preview supplies the cross-built binary. Packaging/build logs record Clang and
MinGW versions; the cross-build currently emits legacy header warnings.

## Next work

Add a synthetic rail and implement the rail/environment dependency cone, then
bring native runtime handles into the Rust backend and import normalized map
collision. Preserve deterministic traces at each step. Character importers and
animation should remain independent of map and physics selection; see ROADMAP.
