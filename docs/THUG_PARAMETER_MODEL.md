# THUG parameter model — v0.4

The actual skating constants come from `Scripts/game/skater/physics.q`.
`GetPhysicsFloat` / `GetPhysicsInt` in `Code/Sk/Objects/skater.cpp` first query
the `skater_physics` structure and then fall back to globals.

v0.4 captures the direct constants referenced by `SkaterCorePhysicsComponent.cpp`
in `native/thug_adapter/config/thug_core_physics_defaults.json`.

Important: stat-backed values are different. THUG's `GetScriptedStat()` interpolates
a `(low, high)` range using a skater stat, then applies switch-stance scaling,
difficulty scaling, and an optional limit. We should preserve that algorithm,
not flatten those values.

For first bring-up, lock all stats to the THUG default 5.0 and medium difficulty,
while still using the original interpolation rules.
