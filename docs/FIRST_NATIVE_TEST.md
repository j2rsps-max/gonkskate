# First native test specification

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

The Rust crate `gonkskate-thug-ffi` already contains the callback implementation for this world.

## Test sequence

Run at a deterministic 60 Hz.

### Stage A — idle
Spawn at `(0, 0, 0)` facing +Z.

Expected:
- state remains `GROUND`
- vertical velocity remains stable
- collision queries hit the plane

### Stage B — movement
Hold forward for 120 frames.

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
