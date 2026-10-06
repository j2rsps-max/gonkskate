# GonkSkate v0.8.0

Experimental host/runtime research project for loading skating gameplay systems
independently from map origin.

The [downloads branch](https://github.com/j2rsps-max/gonkskate/tree/downloads)
provides the prebuilt Windows ZIP through GitHub. See the
[first owner Windows validation](docs/WINDOWS_VALIDATION.md) for confirmed results.

**Open `GONKSKATE.cmd` from the full Windows package.** The hub saves your Skate
installation, keeps a local map library, checks imported areas using real THUG,
and collects each action into one results ZIP. Follow [START_HERE.md](START_HERE.md)
for the capture/workshop milestone and verified scope.

v0.8.0 adds a visual map workshop: place rail chains, choose spawn and facing,
undo/remove edits, and save a separate library copy for real THUG testing.
Keyboard/mouse and controller authoring are supported. Play now shows native
landing/grind counters, resets after falling below a finite area, and records
session metrics. Capture radius can be selected in the hub.
[Release and test notes](docs/V080_WORKSHOP.md).

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
The latest owner v0.7.1 capture imported 857 triangles, passed standing
ollie/landing/replay, and completed 1,308 interactive ticks with 12 landings and
no native stops. Captures start without rails; workshop annotations enable grinds.
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

## Skate frontend development checkpoint

Real THUG now builds as an embeddable Windows DLL/Linux library. Optional Skate
source staging links it and checks its ABI at startup. Native library traces
match the existing executable, including rails and the 10,000-tick run.
A source-backed THUG character importer now pairs skeleton and skin geometry
into a local rigged GLB, preserving original weight/material/LOD metadata.
`RUN_CHARACTER_CHECK.cmd` runs asset-free format checks and optionally imports
a local matched pair, with diagnostic-only result ZIPs.
See [runtime checks and frontend build helper](docs/THUG_EMBEDDED_RUNTIME.md)
and [character import progress](docs/CHARACTER_IMPORT_PROGRESS.md).
Live Skate player attachment, retail character validation, textures and animations remain pending.

The development source now stages an opt-in presentation probe into pinned
Skate3Recomp. Ten existing wrappers observe actor poses, animation jobs,
view membership and caller addresses while preserving original game calls.
A bounded recorder and analyzer report losses and ambiguous identities.
Linux and Windows fixture checks pass; controlled-player ownership and the
authoritative physics tick still require live-game investigation.
See [probe evidence, build checks and the next checkpoint](docs/SKATE3_GUEST_PROBE.md).
The published v0.8.0 ZIP remains the workshop/controller test package.
