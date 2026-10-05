# GonkSkate v0.6.1 — THUG rail and ramp test area

Real THUG ground/air code now runs outside the normal rendered THUG game loop.
The test area has a synthetic floor, a grind rail, a ramp, a placeholder skater and follow camera.

Extract the full Windows playable package into a writable folder and run:

```powershell
.\RUN_PLAYABLE.cmd
```

W pushes, A/D steer, S brakes. Hold Space to crouch; release it to ollie.
Hold E to grind; press R to reset. Escape quits. Keyboard and basic controller mappings are supported.
Python 3 is required; the package includes Godot and the native x64 executable.

Return `logs\GonkSkate-playable-results-*.zip` after testing. A failed launch also
produces that bundle. For a hands-free integration check:

```powershell
.\RUN_PLAYABLE.cmd --area-autotest
```

Read [test area progress](docs/TEST_AREA_PROGRESS.md) for verified results,
build commands and profile limits. Windows native checks pass under Wine;
actual Windows hardware testing remains outstanding.

The Rust host remains cumulative and its selectable physics backends are still
prototypes. This preview uses real native THUG physics through a process bridge.
History packages and the v0.5.1 PowerShell harness fixes remain intact.
`RUN_FIRST_TEST.cmd` runs the older readiness harness.
