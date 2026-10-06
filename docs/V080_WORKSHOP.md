# v0.8.0 — shared-world rail and spawn workshop

The owner v0.7.1 capture/play run completed 1,308 ticks and twelve landings
without a native stop. That area had 857 render triangles and zero rails.
v0.8.0 supplies authoring tools to add the missing skating annotations without
changing original THUG motion or pretending they came from Skate's rail data.

## Workflow

Open **GONKSKATE.cmd → Map library → select area → Map workshop**. Pick surface
points to make a rail chain; height offsets use inches. Nearby vertices on the
picked face snap within 0.3 m. Set height to zero for an existing ledge top, or
24 inches for a practice rail above the floor. Finish the chain, choose a flat
spawn and camera-facing direction if needed, then **Save copy and test with THUG**.

The workshop uses Godot collision solely to pick authoring surfaces. Gameplay
continues to query the normalized world through the native adapter and authentic
CFeeler/core/rail-manager code. The shared world renderer introduces no Godot
gameplay physics. Rail tubes visualize annotations; they are not solid obstacles.

Save emits a bounded private annotation patch. Python checks the source native
world SHA256, validates float32 positions/rails, preserves collision geometry and
import provenance, writes a unique local-worlds/workshop-*.json, and registers
it in the remembered library. A native flat-spawn/ollie/landing/replay check runs
before play. Failed copies remain available for correction. Cancel discards the
draft; the parent world is never overwritten. Unknown/peripheral THUG paths keep
their explicit failure behavior.

The short-test-rail shortcut places a 24-inch-high straight chain from 540 to
780 inches along the spawn direction. It is an annotation, so inspect the ground
and surrounding geometry before saving it. It cannot infer a safe route in an
arbitrary capture. Existing full-map rails survive in the new copy.

## Play and diagnostics

The HUD counts real native landing flags, RAIL entries and fixed-tick rail time.
Scene health also records ground/air/rail ticks, distance, maximum velocity and
resets across recovery segments. Reset jumps are excluded from distance.
Falling 600 inches below the lowest finite-world surface requests native Reset
on the next tick; this adds no fabricated landing. Infinite-floor tests retain
their normal behavior. A reset also returns the camera immediately to the skater.

Capture radius is selectable at 25/50/100 m and remembered in hub settings.
Scene coverage is still limited by the renderer's actual recording. Each action
produces one milestone ZIP; editor patches and worlds stay private. Play exports
only that child's declared trace segments, preventing simultaneous tests from
mixing unrelated sessions.

## Evidence and limits

Four authoring/preservation/privacy tests plus real editor UI tests exercise floor
picking, vertex snap, rail height/chains, spawn constraints, undo/removal, visible
720p save controls, controller navigation/placement and save. The resulting patch
goes through the actual library save path, native acceptance and rail simulation.
Linux and Windows Godot/native executables under Wine both reach
GROUND → AIR → RAIL → AIR → GROUND, with 20 rail ticks, landing at frame 142,
correct spawn reset and identical replay/CSV hashes across platforms.

The actual hub workshop child/save/library-refresh/result-export pipeline passes
on Linux. Client checks cover a 360-tick controller run with one landing and
49 rail ticks, a 400-tick finite-floor run with three automatic resets and no false
landings, and two deliberate native deaths followed by controller/keyboard
recovery. The production launcher still returns failure after that fault-injection
run. Rust workspace tests pass (three FFI tests); the unchanged native regression
profile remains verified with 10,000 ticks, 55 landings and 49 rail ticks.

The new Windows workshop needs owner testing, particularly annotations on actual
captured geometry. The cloud has no retail world or guest generated build.
Skate3Recomp remains the intended main application; player ownership, guest
transform/scheduler/collision hooks and live THUG mode inside it remain pending.
Original Skate collision/rails/materials/textures and full THUG tricks/bails are
not supplied by this release. These authoring tools continue the shared-world
adapter milestone rather than establish those missing integrations.

See [exact owner checks](../TEST_NOTES.md) and [Windows evidence](WINDOWS_VALIDATION.md).
