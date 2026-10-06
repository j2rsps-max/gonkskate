# v0.7.1 owner test

For this hotfix, update the existing folder as described in [START_HERE.md](START_HERE.md).
Run the milestone check, then play the **same saved Skate area**. Hit walls on the
ground and in the air, hold Y/E near the geometry that stopped the old version,
ride off ledges and reset. You can skip recapture. If another unsupported feature
stops physics, press Back/View or R; finish with Escape and return the milestone
ZIP. That session remains marked failed even after recovery, so we can investigate.
The captured area has no annotated rails; use the courtyard for actual grinds.

The original capture checklist remains below.

Open **GONKSKATE.cmd** from the extracted full Windows package.

1. **Run milestone check** must finish with PASSED.
2. Link your installed Skate3Recomp; **Play original Skate** should retain its
   usual game/controller behavior. Quit normally to save the test results.
3. **Capture Skate area and test**: enter a level, stop on a flat area, F10 once,
   wait for disk activity, then quit Skate. THUG checks spawn/ollie/landing before
   opening the captured area. Try pushing, turning, braking and several ollies.
4. Close the test with Escape. Restart the hub and confirm the map is still in
   **Map library**; **Play with THUG** should open that saved area again.
5. Return the newest `logs\GonkSkate-milestone-results-*.zip` for each action you
   tested, especially the capture or any failure. No console copying is needed.
   Say whether the captured floor, controller and landings worked, and mention
   your installed Skate3Recomp version if capture produced no scene.

Several GB free space are needed for F10 capture. Keep ISO, `.gsnap`, recorded
buffers and imported world files local. Use the courtyard if capture is unavailable.

The imported scene runs in the THUG test window. Live THUG control of Skate's own
player, original Skate collision/rails/materials and full trick/bail behavior are
pending. See [release notes](docs/V070_MILESTONE.md) and [start here](START_HERE.md).
