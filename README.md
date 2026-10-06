# GonkSkate v0.7.1

Experimental host/runtime research project for loading skating gameplay systems
independently from map origin.

The [downloads branch](https://github.com/j2rsps-max/gonkskate/tree/downloads)
provides the prebuilt Windows ZIP through GitHub. See the
[first owner Windows validation](docs/WINDOWS_VALIDATION.md) for confirmed results.

**Open `GONKSKATE.cmd` from the full Windows package.** The hub saves your Skate
installation, keeps a local map library, checks imported areas using real THUG,
and collects each action into one results ZIP. Follow [START_HERE.md](START_HERE.md)
for the capture milestone and [release notes](docs/V070_MILESTONE.md) for verified scope.

v0.7.1 fixes native stops reached by the owner's first real Skate capture: wall
bonks, wall-push notifications and leaving a surface. It also adds controller/
keyboard recovery and correct failure reporting. [Hotfix and retest notes](docs/V071_HOTFIX.md).

## Current project rule

The main playable application will be Skate3Recomp, with its original Skate
gameplay and selectable authentic THUG skating. Godot remains the native-adapter
test harness. See [integration direction and importer priorities](docs/INTEGRATION_DIRECTION.md).
Live guest gameplay/world hooks are still pending.

- maps are data;
- gameplay/physics is a selectable backend;
- only one skating backend is authoritative at a time.

Long-term combinations include:

- THUG map + THUG physics
- THUG map + Skate 3 physics
- Skate 3 map + THUG physics
- Skate 3 map + Skate 3 physics

## First cross-world test

The runtime loads worlds without rebuilding. Select the original courtyard in
the hub's map library, or **Capture Skate area and test** to import local Skate
scenery and open it with authentic THUG physics after an automatic spawn/ollie/landing check.
Read [capture and import instructions](docs/SKATE3_WORLD_IMPORT.md).
The owner's first retail capture imported 5,415 triangles and passed standing
ollie/landing/replay; contact issues found during play are addressed in v0.7.1.
This uses visible triangles with generic concrete, not original Skate collision or gameplay.

## First playable preview

Run `RUN_PLAYABLE.cmd` from the full Windows preview package. It includes a
synthetic floor, ramp, grind rail, placeholder skater, follow camera and keyboard/controller input.
THUG supplies authentic ground/air and rail movement. Hold Space and release to ollie;
hold E to grind and press R to reset.
Read [START_HERE.md](START_HERE.md) and [test area progress](docs/TEST_AREA_PROGRESS.md).
The historical archives under `history/` remain unchanged.

## Legal/content boundary

This package contains no retail THUG/THUG2/Skate 3 game assets. Future import
tools should operate on files supplied locally by the user from their own copies.

## Current native progress

The standalone executable compiles real THUG core/state/rotation/math code at
60 Hz. The presentation client sends input and reads authoritative native state.
The Rust FFI links the tested native stat evaluator. The next priority is live
integration with the Skate3Recomp frontend. Rust's selectable THUG/Skate3 simulation
backends are still prototypes. Original rail acquisition and rail physics now run against a synthetic rail.
Shared triangle geometry drives native collision and rendering. Balance, trick
animations, scoring and bails remain future work. Runtime imported triangles are
supported; authentic game-format collision and metadata import remain pending.

Controller support is required for both gameplay backends. See
[controller support](docs/CONTROLLER_SUPPORT.md) for mappings, tests and current limits.

## Skate 3 input preparation

`RUN_SKATE3_CHECK.cmd` captures both sticks/triggers in a live controller lab and
checks guest packets encoded against the actual pinned ReXGlue SDK. Optional
local game-file checks inspect metadata and known TU3 hashes. A separate upstream
reference launcher is available; authentic Skate gameplay inside GonkSkate is pending.
Read [test notes](TEST_NOTES.md) and [verified input boundary](docs/SKATE3_INPUT_PROGRESS.md).

If Skate3Recomp is already running on Windows, `RUN_SKATE3_REFERENCE.cmd --inspect-only`
automatically locates it and gathers metadata without starting another instance.
The host controller driver now registers with the original SDK InputSystem and
preserves menu/UI gating, connection status and optional rumble feedback.
See [driver integration](docs/SKATE3_DRIVER_INTEGRATION.md). Live guest transport,
Skate simulation hooks and collision-world adaptation remain pending.
