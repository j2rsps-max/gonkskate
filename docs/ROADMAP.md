# GonkSkate roadmap

Main application decision: Skate3Recomp with original Skate gameplay and
selectable THUG gameplay. See [integration direction](INTEGRATION_DIRECTION.md).
Keep the standalone courtyard as a regression harness.

v0.7.0 adds one owner-facing hub, a persistent map library, authentic imported
spawn/ollie/landing acceptance, and unified result exports. The immediate owner
milestone is [capturing and skating a local Skate area](V070_MILESTONE.md).

## Phase 0 — host architecture
- [x] Rust workspace
- [x] shared map manifest
- [x] switchable physics backend
- [x] deterministic no-render test loop
- [x] initial C ABI design
- [x] world-query callback ABI for THUG adapter

## Phase 1 — THUG extraction / adapter
- [x] locate primary skating simulation class
- [x] locate state-specific physics functions
- [x] locate line/world collision seam (`CFeeler`)
- [x] locate transform / velocity ownership
- [x] define first THUG C ABI
- [x] enumerate all components required by `CSkaterCorePhysicsComponent::Finalize()`
- [x] isolate direct core physics/script-parameter dependencies
- [x] preserve stat-backed physics interpolation without full script VM
- [ ] build standalone THUG adapter library against kisak-thug
- [x] boot real THUG ground physics against a synthetic flat plane
- [x] real ollie / airborne / landing loop
- [x] real rail acquisition + rail movement against synthetic rail
- [ ] authentic grind balance, scoring and animation integration
- [ ] supported tricks and bail/recovery behavior

## Phase 2 — normalized world
- [x] triangle collision representation for the synthetic area
- [x] per-triangle THUG terrain IDs and collision flags
- [ ] rail spline representation
- [x] callback implementation for segment/triangle raycasts
- [x] synthetic rail ingestion into original THUG rail manager
- [x] general multi-rail ingestion into original THUG rail manager
- [ ] callback-backed rail lookup
- [x] runtime world selection, validated binary transport and indexed collision
- [x] triangulated OBJ and Skate render-recording importers with original demo/format fixtures
- [x] unified importer command with explicit format/unit boundaries
- [x] validate one retail Skate render capture on owner hardware (basic spawn/ollie/landing and movement; contact issues found, v0.7.1 retest pending)
- [ ] import one THUG level's collision
- [ ] run real THUG physics on imported THUG collision

## Phase 3 — Skate 3 boundary research
- [x] confirm current native recomp foundation and renderer status
- [x] confirm generated/recompiled game logic is hosted through ReXGlue
- [x] identify guest controller ingestion path (ReXGlue InputSystem → XamInputGetState)
- [x] validate full controller guest packet encoding against real SDK types
- [x] local controller lab, game metadata probe and reference-run diagnostics
- [x] implement host input driver against original SDK InputSystem, with connection status and UI gating
- [ ] attach live host input transport to a source-built Skate guest
- [ ] identify guest player transform addresses/symbols
- [ ] identify simulation tick / scheduler hook
- [ ] identify collision-world coupling
- [ ] add deterministic state tracing
- [ ] define Skate 3 C ABI adapter

## Phase 4 — cross-map proof
- [ ] normalize one small Skate 3 collision area
- [x] real THUG physics on source-derived Skate-format geometry fixtures
- [x] real THUG physics on a locally captured retail Skate render area (owner validated ground/air)
- [ ] normalize one THUG collision area
- [ ] Skate 3 physics on THUG geometry
- [ ] map + physics selection UI

## Additional map format research

Tony Hawk and Skate formats remain first. Each supported source needs a converter
and verified collision/placement/skating metadata; file extensions alone are not
enough. Existing OBJ exports can use the neutral importer today.

- [ ] THUG Pro custom map/package compatibility and THUG2-specific differences
- [ ] other Tony Hawk game/platform variants
- [ ] Skate 1/2 and general Skate 3 mod/package formats
- [ ] Session source exports and packaged mod formats
- [ ] Skater XL source exports and packaged mod formats
- [ ] richer neutral mesh/material formats, including glTF and FBX

## Playable preview
- [x] standalone real-core ground/air test and Windows x64 binary
- [x] synthetic floor, placeholder skater, follow camera and basic controller/keyboard input
- [x] deterministic native session traces and replay checks
- [x] shared rail/ramp geometry, grind/reset controls and slope orientation
- [x] owner Windows courtyard rendering/controller/ground-air/basic-grind validation
- [ ] owner keyboard and physical disconnect/reconnect validation
- [ ] integrate real runtime handles into the Rust backend

## Independent skater appearance and character imports

Character appearance must be selected independently of map, physics, scoring,
camera and rules. A THPS character on a THUG map with another physics backend
should not require that character's original game's movement system.

- [ ] normalized character package: mesh/materials, skeleton, animation mapping,
      source-game provenance and importer version
- [ ] import user-supplied Tony Hawk character files, covering THPS and later games
- [ ] include hidden/guest character imports such as Spider-Man when source
      formats and compatible rigs have been verified
- [ ] research character formats from Skate 1, 2 and 3
- [ ] support compatible modded Skate 3 character packages after base import works
- [ ] character selector and per-rig animation retargeting

These are proposed capabilities, not confirmed format support. Importers operate
on local game/mod files; retail character assets are not bundled. Keep the
procedural mannequin until ground/air, rails and imported world collision are
stable. Animation fidelity will require its own validation rather than assuming
all games share a skeleton.

## Required controller support for both backends

Controller play is a release requirement for THUG and Skate, including USB and
wireless Xbox/PlayStation-compatible devices where the host supports them.

- [x] THUG preview: configurable button bindings, deadzones, D-pad, pause/reset
- [x] preserve both sticks and both analog triggers independently in controller traces
- [x] deterministic controller-event input through the original THUG core
- [x] pause on active-controller disconnect; reconnect and resume without stale input
- [ ] owner validation on real Windows hardware, USB and wireless
- [ ] in-game binding/device selection and calibration UI
- [ ] integrate device snapshots into the Rust host/backend input boundary
- [ ] authentic Skate dual-stick/Flick-It and trigger injection after locating its input boundary
- [ ] independently saved THUG/Skate control profiles and controller-aware prompts

The Skate backend is still a prototype. Preserving analog readings does not
establish an authentic Skate control adapter. Do not collapse its right stick
into THUG's directional buttons or infer its input boundary without research.

## Shared-world authoring checkpoint — v0.8.0
- [x] visual rail-chain and spawn/facing authoring on imported areas
- [x] separate saved variants, undo, source identity and asset-free diagnostics
- [x] keyboard/mouse and controller workshop input
- [x] editor-created rail through real THUG acquisition/grind/exit/landing/replay
- [x] session counters and native finite-area fall reset
- [ ] owner workshop grind test on captured retail geometry
- [ ] original Skate collision and rail metadata extraction
