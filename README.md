# GonkSkate Windows downloads

Latest: **v0.7.1 — captured-world contact hotfix**.

[Download the full v0.7.1 Windows ZIP](https://raw.githubusercontent.com/j2rsps-max/gonkskate/downloads/GonkSkate-v0.7.1-Windows-Playable-Full-Package.zip)

Updating from v0.7.0: close GonkSkate. Copy the CONTENTS of the ZIP's
GonkSkate-v0.7.1 folder into your existing project folder, replacing included files.
Your user/hub.json, local-worlds and captures are excluded from the package and
remain local. Keep the old ZIP. No recapture is needed.

Open GONKSKATE.cmd, run milestone check, then Map library -> select your existing
Skate area -> Play with THUG. Retest ground/air walls, ledges and holding Y/E near
troublesome geometry. Back/View or R can recover a stopped native process; Escape
finishes. Return logs/GonkSkate-milestone-results-*.zip, even after recovery.

This fixes bonk-sound and audited ground-loss/flail/wall-push event traps. Failures
stay in the results instead of being reported as passed. Four contact/drop cases
pass with identical Linux/Windows traces; child death, controller/keyboard reset
and resumed simulation pass on Linux and Windows under Wine. Full native rail/
ramp/10,000-tick regressions and runtime-world checks pass.

The owner's first Skate capture imported 5,415 triangles and passed standing
ollie/landing/replay, then reached these native stops. Its v0.7.1 contact retest
remains pending. Captured render scenery has generic concrete and no annotated
rails. Use the courtyard for actual grinds. Live THUG control of Skate's own
player, original collision/material/rail import and full trick/bail behavior remain
future work. Read START_HERE.md and docs/V071_HOTFIX.md in the package.

For a fresh installation, extract the full ZIP into a writable folder and open
GONKSKATE.cmd. Python 3 with Tkinter is required; Godot and native x64 executables
are included. Keep several GB free for F10 capture. No retail assets are included.

SHA256: `06f89250c7f9992a5aca37f5c924738d1d974144124a9597546091da101695fa`

## Previous packages

- [v0.7.0](https://raw.githubusercontent.com/j2rsps-max/gonkskate/downloads/GonkSkate-v0.7.0-Windows-Playable-Full-Package.zip)
- [v0.6.6](https://raw.githubusercontent.com/j2rsps-max/gonkskate/downloads/GonkSkate-v0.6.6-Windows-Playable-Full-Package.zip)

[Source and history on main](https://github.com/j2rsps-max/gonkskate/tree/main).
Do not merge this binary downloads branch into main.
