# GonkSkate v0.6.6 — runtime worlds and Skate scenery capture

Development direction: use Skate3Recomp as the main app, preserving original
Skate gameplay and adding selectable authentic THUG skating. The Godot preview
is the regression harness. Read [integration direction](docs/INTEGRATION_DIRECTION.md).

Start with [Skate world import](docs/SKATE3_WORLD_IMPORT.md) for the new combination test.
Try `RUN_PLAYABLE.cmd --world worlds\courtyard.json` immediately, then capture an
area using `RUN_SKATE3_CAPTURE.cmd --exe "YOUR_INSTALLED_SKATE3_EXE"`.
This runs authentic THUG physics on imported render triangles. The first real
Skate capture needs your PC test; Skate guest gameplay is not embedded here.

Real THUG ground/air code now runs outside the normal rendered THUG game loop.
The test area has a synthetic floor, a grind rail, a ramp, a placeholder skater and follow camera.

Extract the full Windows playable package into a writable folder and run:

```powershell
.\RUN_PLAYABLE.cmd
```

W pushes, A/D steer, S brakes. Hold Space to crouch; release it to ollie.
Hold E to grind; press R to reset. Controller Start pauses; Back resets; right stick looks. Escape quits. Keyboard and basic controller mappings are supported.
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

Controller support is required for both gameplay backends. See
[controller support](docs/CONTROLLER_SUPPORT.md) for mappings, tests and current limits.

For a working Skate3Recomp installation, use the small reference-check package or
run `RUN_SKATE3_REFERENCE.cmd --inspect-only` here while Skate is open.
Return the generated `logs\GonkSkate-skate3-reference-results-*.zip`.
