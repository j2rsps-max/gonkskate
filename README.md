# GonkSkate v0.6.6

Experimental host/runtime research project for loading skating gameplay systems
independently from map origin.

To continue on the owner's Windows PC, use the [local setup and handoff](LOCAL_HANDOFF.md).
The [downloads branch](https://github.com/j2rsps-max/gonkskate/tree/downloads)
hosts the verified prebuilt Windows ZIP.

## Current project rule

- maps are data;
- gameplay/physics is a selectable backend;
- only one skating backend is authoritative at a time.

Long-term combinations include:

- THUG map + THUG physics
- THUG map + Skate 3 physics
- Skate 3 map + THUG physics
- Skate 3 map + Skate 3 physics

## First cross-world test

The new runtime loads worlds without rebuilding. Run `RUN_PLAYABLE.cmd --world worlds\courtyard.json`
for an original OBJ demo. `RUN_SKATE3_CAPTURE.cmd --exe "YOUR_INSTALLED_SKATE3_EXE"`
can capture local Skate scenery and open it with authentic THUG physics.
Read [capture and import instructions](docs/SKATE3_WORLD_IMPORT.md).
Source-format fixtures pass; the first owner retail capture remains unverified.
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
The Rust FFI links the tested native stat evaluator; integrating the full native
runtime into the Rust backend is next. Rust's selectable THUG/Skate3 simulation
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
