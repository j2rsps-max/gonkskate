# v0.6.1: THUG rail and ramp test area

This release adds a straight grind rail and a ramp to the first playable preview.
Native THUG remains authoritative. Godot renders the geometry and sends input;
it does not simulate skating movement. No retail game assets are included.

## Run on Windows

Extract `GonkSkate-v0.6.1-Windows-Playable-Full-Package.zip` into a writable
folder and run `RUN_PLAYABLE.cmd`. Python 3 is required; Godot 4.4.1 and the
native x64 executable are included.

| Action | Keyboard | Controller |
| --- | --- | --- |
| Push | W / Up | Left face button (Xbox X) |
| Steer | A/D / Left/Right | Left stick left/right |
| Brake | S / Down | Left stick down |
| Crouch / ollie | Hold Space, release to ollie | Hold bottom face button, release |
| Grind | Hold E near the rail | Hold top face button (Xbox Y) |
| Reset to spawn | R | Keyboard R |
| Quit | Escape | Keyboard Escape |

The rail is straight ahead. Push, crouch and release Space to jump toward it,
holding E to acquire the rail. The ramp sits beside it. R resets position,
velocity and the core state using original THUG initialization/reset routines.
Stick directions are currently digital. The mannequin has no trick animations.

For a scripted rail integration check:

```powershell
.\RUN_PLAYABLE.cmd --area-autotest
```

`--autotest` remains the ground/air check. Both modes and interactive sessions
save output, native CSV and peripheral-call diagnostics in
`logs\GonkSkate-playable-results-*.zip`. Return that ZIP after testing on Windows.

## Authentic code and environmental adaptations

The whole upstream `rail.cpp` joins the original core/state/rotation/math/button
code. Original `maybe_stick_to_rail()`, `got_rail()`, `do_rail_physics()` and grind
selection execute through the normal core `Update()` order at a fixed 60 Hz.
The environmental loader creates linked original `CRailNode` objects using
original `CRailManager::NewLink()`. A portability fix replaces the original
32-bit pointer casts in rail index calculation with native pointer subtraction.

`worlds/test_area.json` defines inch-based triangle coordinates, flags, terrain
and a two-point rail. Native collision and Godot rendering read the same source.
The native build currently bakes that data into the executable; it is not yet
a runtime map importer. Launch checks its hash against the build manifest and
requires a rebuild if it differs. The Windows package supplies that matching
binary; source cross-build instructions remain in FIRST_PLAYABLE_TEST.md.

The six triangles form a 72-inch-high ramp. Segment/triangle collision supports
finite endpoints, two-sided queries, original winding normals, nearest/farthest
hits and collision flag masks. The floor remains an infinite plane. The original
core handles slope contact and motion; presentation uses its up/forward vectors.
Rail supports are visual decorations, not collision obstacles.

## Verified behavior

- Ground/air, steering, braking, 10,000 ticks with 55 ollies, deterministic replay,
  IPC equivalence, malformed input and fail-fast peripheral checks still pass.
- The rail scenario follows GROUND → AIR → RAIL → AIR → GROUND, spends 49 ticks
  grinding, uses metal terrain and exits past the rail end. Original grind
  selection resolves the captured `GrindTrickList` rather than inventing a trick.
- Crouching on the rail and releasing at frame 210 produces original grind-jump
  velocity and a later landing. Live rail input replays byte-identically.
- Reset during a grind returns position and velocity to zero and removes rail
  state. Ramp traversal remains grounded, rises to 72 inches and returns to the
  floor with normals matching the triangle slopes.
- Linux X11 keyboard-event injection verifies push, crouch/release, rail acquisition
  with E, reset with R, steering, braking and Escape through interactive input.
  That recorded session replays byte-identically in the native executable.
- Native suites pass on Linux and Windows x64 under Wine. The Godot scene's
  fixed-tick rail check passes on Linux and under Wine. Actual Windows hardware
  and controller testing remain outstanding.
- Rust workspace, C++ stat/plane/mesh checks, script parser checks and 20,000-case
  stat comparison remain part of the readiness harness.

CSV preserves the first 22 columns and adds `grind,reset,ux,uy,uz`. Native pipe
input accepts five legacy binary fields, an optional sixth grind field, and an
optional seventh reset field. Internal THUG state 4 means RAIL; it is not the
public ABI enum. Runtime-handle C ABI integration remains pending.

## What still needs work before importing maps

Grind balance, scoring and trick animation are absent. Selected grind scripts
are logged by a presentation facade; the script VM does not run them. Balance
is not silently claimed as functional. Extra grind tricks and score changes
have explicit instrumented responses. Unsupported dependencies still fail fast
with a frame and symbol diagnostic.

The next work is to integrate real balance and supported trick/bail behavior,
then validate a richer synthetic area and general rail ingestion before importing
one locally supplied THUG map. Moving objects, triggers and script-driven world
behavior require their own adapters. Character import stays independent of map
and physics; the cross-game/hidden-character goals remain in ROADMAP.md.
