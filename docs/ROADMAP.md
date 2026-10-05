# GonkSkate roadmap

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
- [ ] preserve stat-backed physics interpolation without full script VM
- [ ] build standalone THUG adapter library against kisak-thug
- [ ] boot real THUG ground physics against a synthetic flat plane
- [ ] real ollie / airborne / landing loop
- [ ] real rail acquisition + grind against synthetic rail

## Phase 2 — normalized world
- [ ] triangle collision representation
- [ ] material / terrain IDs
- [ ] rail spline representation
- [ ] callback implementation for raycasts
- [ ] callback implementation for rail lookup
- [ ] import one THUG level's collision
- [ ] run real THUG physics on imported THUG collision

## Phase 3 — Skate 3 boundary research
- [x] confirm current native recomp foundation and renderer status
- [x] confirm generated/recompiled game logic is hosted through ReXGlue
- [ ] identify controller injection point
- [ ] identify guest player transform addresses/symbols
- [ ] identify simulation tick / scheduler hook
- [ ] identify collision-world coupling
- [ ] add deterministic state tracing
- [ ] define Skate 3 C ABI adapter

## Phase 4 — cross-map proof
- [ ] normalize one small Skate 3 collision area
- [ ] THUG physics on Skate 3 geometry
- [ ] normalize one THUG collision area
- [ ] Skate 3 physics on THUG geometry
- [ ] map + physics selection UI
