# GonkSkate v0.7.1 — start here

Updating from v0.7.0: close the hub/test window, then copy the **contents** of
the new package's `GonkSkate-v0.7.1` folder into your existing GonkSkate folder,
replacing included files. The package contains no `user/` or `local-worlds/` data,
so your saved installation, captures and map library remain. Keep the older ZIP.
Run **GONKSKATE.cmd → Run milestone check**, then select your existing Skate area
in **Map library → Play with THUG**. Retest the walls/ledges that stopped physics;
you do not need a new capture. Return the new milestone-results ZIP.
See [hotfix notes](docs/V071_HOTFIX.md).

Extract the full Windows ZIP into a writable folder. Double-click
**GONKSKATE.cmd** to open the hub. Python 3 with Tkinter is required; the standard
python.org Windows installer includes it. Godot and both tested native x64
executables are included. No compiler or Rust installation is needed to play.

1. Click **Run milestone check**. Wait for PASSED. This checks real THUG ground/air,
   rail and controller behavior, plus the original ReXGlue input bridge using
   synthetic input. It does not replace a physical-controller play test.
   **Check my controller** opens the optional live stick/trigger/button lab; Escape finishes it.
2. Click **Find in Downloads**, or **Browse executable**, and choose your installed
   Skate3Recomp `skate3.exe`. The hub remembers it. **Play original Skate** opens
   your normal Skate game with its original controls.
3. Click **Capture Skate area and test**. Close any existing Skate window first.
   In the game, enter a level, stop on an open flat area, press **F10 once**, wait
   for disk activity to finish, then quit Skate normally. Keep several GB free.
   The hub imports the captured geometry, checks a real THUG standing ollie and
   landing, then opens that area in the THUG test window.
4. Try pushing, steering, braking and several ollies. Xbox **X** pushes,
   **A** crouches/releases ollie, **Y** holds grind; left stick steers/brakes,
   right stick looks, Start pauses, Back resets. Keyboard: W/A/D/S, Space, E, R.
   Escape closes the test. Imported Skate render captures currently contain no
   rail annotations. Falling outside the captured area requires reset.
5. In **Results**, click **Open results folder** and return the newest
   `GonkSkate-milestone-results-*.zip`. One ZIP includes the child checks and
   traces. Tell me whether the captured floor and landings looked correct.

Your library appears under **Map library** and survives restarts. It includes our
original courtyard for testing without game files. Import normalized world JSON,
triangulated Y-up OBJ (explicit units), or an existing Skate `.scene.jsonl` with
its `.buffers.bin` and `.gsnap` companions. **Check map** repeats the acceptance
check. **Adjust spawn** creates a copy with a new spawn in world inches.

If the capture fails, return the same milestone ZIP. An older Skate3Recomp release
may lack native-render snapshot support. A sloped or unsupported spawn can fail
this flat-surface check; the imported map remains in the library for diagnosis.

This milestone runs authentic THUG skating on locally captured Skate render
triangles in a separate test window. Live THUG control of Skate's own player is
still pending. Captures use generic concrete; original collision, materials,
textures, rails and full trick/bail behavior are future work. Skate3Recomp remains
the intended main application; see [integration direction](docs/INTEGRATION_DIRECTION.md).

The ISO, memory captures, imported geometry and saved installation path stay on
your PC. Keep old working packages. To carry older maps into this release, use
**Import map** and select their JSON under the old `local-worlds` folder.
See [milestone notes](docs/V070_MILESTONE.md) for verification and command-line use.
The old `RUN_PLAYABLE.cmd` and readiness scripts remain available.
