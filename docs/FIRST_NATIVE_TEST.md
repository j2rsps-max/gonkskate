# First native test specification

Ground/air stages are now implemented in the v0.6.0 flat-floor profile. See
[FIRST_PLAYABLE_TEST.md](FIRST_PLAYABLE_TEST.md) for commands and validation.

## Purpose

Prove that **real THUG core physics** can execute without the normal THUG renderer or level loader.

## World

Synthetic:
- infinite plane at `y = 0`
- normal `(0, 1, 0)`
- generic concrete terrain
- no rails
- no moving objects
- no triggers

The authoritative first runtime uses the versioned C++ callback in
`native/thug_adapter/src/thug_flat_world.cpp`. Rust retains its earlier illustrative
callback for future host integration.

## Test sequence

Run at a deterministic 60 Hz.

### Stage A — idle
Spawn at `(0, 0, 0)` facing +Z.

Expected:
- state remains `GROUND`
- vertical velocity remains stable
- collision queries hit the plane

### Stage B — movement
Hold THUG square/push input (mapped to W); forward alone does not initiate a push.

Record:
- position
- velocity
- state
- terrain

Success:
- real THUG acceleration / rolling behavior advances the skater
- no renderer or map system is required

### Stage C — ollie
Inject THUG ollie input / jump call after a short crouch/tense window.

Record every frame:
- position Y
- velocity Y
- state
- landed-this-frame

Success:
- transition `GROUND -> AIR -> GROUND`
- landing is produced by real THUG collision/state code

## Stage D — rail (next test)

Add one synthetic rail:
- from `(0, 0.75, 8)` to `(0, 0.75, 20)`
- tangent +Z

Then verify the real code reaches:
- `maybe_stick_to_rail`
- `got_rail`
- state `RAIL`
- `do_rail_physics`
