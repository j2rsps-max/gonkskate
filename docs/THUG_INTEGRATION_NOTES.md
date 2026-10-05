# THUG integration notes — research pass 1

## Confirmed core physics location

`Code/Sk/Components/SkaterCorePhysicsComponent.cpp` is the primary skating simulation implementation.

The corresponding class is `Obj::CSkaterCorePhysicsComponent`.

Its public `Update()` entry point sits above separate state-specific simulation paths:

- `do_on_ground_physics()`
- `do_in_air_physics()`
- `do_wallride_physics()`
- `do_wallplant_physics()`
- `do_lip_physics()`
- `do_rail_physics()`

This is the strongest integration point found so far.

## High-value behaviors already isolated by name

### Basic movement
- `limit_speed`
- `do_brake`
- `handle_ground_friction`
- `handle_wind_resistance`
- `handle_rolling_resistance`
- `do_kick`
- `do_jump`

### Collision / ground tracking
- `snap_to_ground`
- `check_side_collisions`
- `handle_forward_collision`
- `handle_forward_collision_in_air`
- `handle_upward_collision_in_air`
- `push_away_from_walls`

### THPS-specific transitions
- `check_for_wallride`
- `check_for_wallplant`
- `maybe_spine_transfer`
- `maybe_acid_drop`
- `enter_acid_drop`

### Rail/grind behavior
- `maybe_stick_to_rail`
- `will_take_rail`
- `got_rail`
- `do_rail_physics`
- `skate_off_rail`
- `do_grind_trick`

## Authoritative skater state

The component reads/writes the owning object's:

- `m_pos`
- `m_old_pos`
- `m_vel`
- `m_matrix`

It also tracks state such as:

- current / previous skating state
- current surface normal
- last ground feeler
- terrain type
- current rail node / rail manager
- landed-this-frame
- vert state
- wall-push state
- rolling friction

## World collision seam

THUG uses `CFeeler` (`Code/Sk/Engine/feeler.cpp`) for line collision queries.

`CFeeler` eventually talks to collision objects / caches and records:

- hit point
- hit normal
- hit distance
- surface data
- trigger/script metadata
- moving-object collision

This suggests a better architecture than replacing the physics:

1. Keep `CSkaterCorePhysicsComponent` and its state machine.
2. Replace/adapt the lower world-query layer.
3. Feed collision results from GonkSkate's normalized world back into THUG-shaped results.
4. Keep THUG's rail/state-transition logic intact.

That is the current preferred approach.

## Adapter milestone

First successful native milestone:

1. construct a minimal skater object and required components;
2. initialize `CSkaterCorePhysicsComponent`;
3. provide synthetic input;
4. provide a flat-plane collision callback;
5. call the real update;
6. read back position / velocity / state through the C ABI.

After that, swap the synthetic plane for a normalized GonkMap collision world.
