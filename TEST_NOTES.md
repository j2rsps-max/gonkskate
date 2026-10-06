# v0.8.0 owner test

Update the existing folder as described in [START_HERE.md](START_HERE.md); keep
your saved map library. Open **GONKSKATE.cmd**.

1. **Run milestone check** must finish PASSED. It includes editor placement,
   authentic grinds, contact behavior, controller mapping, session counters,
   fall reset and intentional child-failure recovery.
2. Select **Gonk courtyard → Map workshop** first. Click **Add short test rail
   ahead**, then **Save copy and test with THUG**. Push toward the yellow line,
   hold/release A to ollie before it, and hold Y to grind. Keyboard: W, Space, E.
   Confirm the HUD switches to RAIL and the grind/rail-time counters increase.
3. Repeat with your saved **Skate captured area**. The shortcut adds a 24-inch
   rail about 14 m along the spawn's blue arrow. Check that it has a clear flat
   approach and landing. If it intersects scenery, undo it and choose another
   spawn/line. You can use the same capture; no new F10 capture is required.
4. For a real ledge, set rail height to **0**, click successive points on its top,
   and press **Enter / Finish rail**. Default height **24** places a practice
   rail above the picked floor. **Z / Undo** reverses points, completed chains,
   spawn changes or removal. Save only after finishing the chain.
5. Try controller authoring: left stick moves, right stick looks, LT/RT moves
   down/up. **A** places at the center marker, **X** finishes, **Y** undoes,
   **Start** saves; **Back** cancels. Scroll the sidebar for reminders. The
   skating window retains its usual X push / A ollie / Y grind mapping.
6. In the workshop, choose **Set spawn on flat surface** and click a flat floor.
   The blue arrow follows the camera's horizontal viewing direction. Save a
   copy, confirm its acceptance passes, and use Back/R during play to reset there.
   Ride out of the finite capture: after falling well below its lowest surface,
   THUG should reset automatically without a fake landing.
7. Close play with Escape. Confirm the new copy persists in the library and the
   old map still exists. Return the newest **GonkSkate-milestone-results-*.zip**
   from Results → Open results folder for the workshop action. Mention whether
   the grind, controller editing, spawn and automatic reset worked.

Optional: choose a **50 m** capture radius for more scenery. F10 records only
what the native-render capture makes available; a larger crop cannot recover
missing geometry. Captures may occupy several GB. Keep ISO, .gsnap, buffers,
imported worlds and workshop patches local; the result ZIP excludes them.

If an unsupported feature stops physics, Back/View or R restarts it; Escape
finishes and saves the failure even after recovery. Return that milestone ZIP.
Original Skate rail/collision metadata, textures, full THUG trick/bail behavior
and live THUG control of Skate's own player remain pending. This is the shared
world/native-physics test window, while Skate3Recomp remains the main-app target.
