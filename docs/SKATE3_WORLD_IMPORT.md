# v0.6.6: Skate scenery + authentic THUG physics

This update makes the first combination practical to try: capture a visible
piece of Skate 3 on your PC, import its triangles, then run original THUG skating
on those triangles. The THUG executable loads worlds at launch; changing the
world needs no C++ rebuild. Godot draws exactly the float32 geometry given to
the native collision bridge. Controller mappings remain the THUG profile.

The format importer and real-core path pass source-derived fixtures on Linux
and Windows under Wine. The owner also validated the synthetic courtyard and
controller on Windows; its 2,234-frame live trace replays exactly on Linux.
See [Windows validation](WINDOWS_VALIDATION.md). No retail Skate capture has been tested in the cloud.
Your first local capture is the next validation step. This is a render-geometry
proof, with concrete collision, a procedural skater and simple materials.
Skate's original collision, materials, rails, textures and gameplay are absent.

## Immediate test without game files

Extract the full v0.6.6 Windows package into a writable folder. Python 3 is the
launcher prerequisite; Godot and both native executables are included.

```powershell
.\RUN_PLAYABLE.cmd --world worlds\courtyard.json
```

This is our original synthetic OBJ courtyard, raised 120 inches, with a ramp
and two separately annotated rails. It proves world selection, spawn/reset and
multiple rail chains without assets or compilation. It is not a Skate map.
Xbox X pushes, A crouches/releases ollie, Y holds grind; left stick steers/brakes,
right stick looks, Start pauses and Back resets. Keyboard: W/A/D/S, Space, E, R.
Escape quits. There is no hidden infinite floor outside this finite courtyard.

## Capture your installed Skate3Recomp

The capture launcher targets native-render diagnostics at upstream
`f6e0ae87fdfecbadb5c1e36c55d66a744187a3cd` (v2.0.0). Your installed executable
must include these diagnostics. Older releases may produce no capture; the
launcher reports this rather than importing invented scenery.

Close the existing Skate3Recomp window. From the extracted GonkSkate folder,
replace the example path with your actual installed executable:

```powershell
.\RUN_SKATE3_CAPTURE.cmd --exe "C:\Users\YOUR_NAME\Downloads\Skate3Recomp\skate3.exe"
```

1. The helper starts your installed game with temporary capture CLI flags. Enter
   a level and stop on a clear, flat outdoor area with the normal gameplay camera.
2. Press **F10 once**. Allow disk activity to finish; the memory snapshot can
   occupy several GB and temporarily stall the game. Keep several GB free.
3. Quit Skate3Recomp normally. The helper imports the latest captured area and
   opens GonkSkate with real THUG physics and your usual controller controls.
4. Try pushing, steering, braking and several ollies/landings. Back or R returns
   to the captured spawn after falling outside the area. Escape finishes.

The default crop has a 25-meter radius around the camera's X/Z position. If
it is too small, reuse the capture with `--radius 60` or another value up to 200.
The importer chooses the highest supporting surface below the camera. A camera
inside a building or below a surface can require an explicit `--spawn X Y Z`
in **source meters**, not GonkSkate inches. Unsupported triangles are excluded;
missing geometry may leave holes. Bail/recovery, moving objects, trigger scripts
and complex-world behavior still need implementation; unsupported dependencies
fail with diagnostics. Reaching a new map does not prove all THUG states work.

## Retry an existing capture

The console prints the result and local capture folder paths. Substitute the
actual capture filename:

```powershell
.\RUN_SKATE3_CAPTURE.cmd --scene "logs\skate3-capture-TIMESTAMP\local-capture\snapshot_SECONDS.scene.jsonl" --radius 60
```

The `.scene.jsonl`, `.buffers.bin` and `.gsnap` companions must remain together.
`--no-play` imports without launching. Imported worlds are saved under ignored
`local-worlds\`; the printed JSON path can be passed to `RUN_PLAYABLE.cmd --world`
for subsequent runs. Installed game files, configurations and saves are not
edited by the helper. Normal game startup can update the game's own files.

Return the newest `logs\GonkSkate-skate3-capture-results-*.zip` and
`logs\GonkSkate-playable-results-*.zip`, plus the installed Skate3Recomp release
version and whether the floor/landings worked. These ZIPs exclude captures and
world geometry. Keep the ISO, memory snapshots and imported geometry local.
Release packages contain only our original demo geometry and code/tooling.

## Other geometry and reproduction

Triangulated OBJ files use explicit units and optional Z-up/winding conversion:

```powershell
py -3 tools\import_obj_world.py my-area.obj --units meter --spawn 0 0 0 --output local-worlds\my-area.json
.\RUN_PLAYABLE.cmd --world local-worlds\my-area.json
```

OBJ spawn coordinates are output inches; Skate capture spawn overrides are input
meters. OBJ material names are not converted into authentic skating metadata.
These importers do not decode a THUG level archive or an ISO.

The native `GNKWLD1` transport validates version/counts, float32 geometry,
spawn/facing, terrain and rail chains. Its BVH preserves existing nearest/farthest,
flag filtering and stable tie selection. Tests compare 15,000 seeded queries
against exhaustive triangle queries and replay imported-world movement exactly.
Multi-rail ingestion preserves THUG's original rail manager and state physics.
World files are loaded before constructing the skater; they are immutable during
simulation. Runtime reload and a world-selection UI remain future work.

The importer follows upstream `WriteRecording`, `WriteMemorySnapshot`,
`ComputeItemFingerprint` and vertex decoders. Snapshot regions are read on
demand, including the physical-map page offset. Static mesh fingerprints must
match scene records; stale memory is rejected. Skinned geometry, dynamic rescue
records and overlay paths are excluded. Accepted rigid geometry is frozen at
the captured transform. No controller or simulation scheduler hook into the live
Skate guest is implied by this importer.

```bash
python3 tools/test_world_import.py --executable build/thug-headless/gonkskate-thug-test
python3 scripts/run-playable.py --world logs/world-import/imported.json --autotest
python3 scripts/run-playable.py --world worlds/courtyard.json --controller-autotest
```
