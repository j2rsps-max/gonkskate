# GonkSkate Windows checkpoints

[Download v0.8.0 — full Windows package](https://raw.githubusercontent.com/j2rsps-max/gonkskate/downloads/GonkSkate-v0.8.0-Windows-Playable-Full-Package.zip)

Close the hub and games. Copy the contents of GonkSkate-v0.8.0 into your existing
project folder, replacing included files. Saved user settings and local-worlds
maps stay in place. Keep your older ZIP.

Open GONKSKATE.cmd → Run milestone check. Then Map library → select an area →
Map workshop. Add a short test rail or trace a ledge, choose a flat spawn, and
Save copy and test with THUG. Test the courtyard first, then your saved Skate
capture. Editing supports mouse/keyboard and controller input, undo and separate
saved variants. Play adds native landing/grind counters and finite-area fall reset.
See TEST_NOTES.md for the owner test. Return the newest milestone-results ZIP.

Verified Linux workflow and Windows Godot/native executables under Wine, including
an editor-created rail through authentic THUG grind/exit/landing and exact replay.
Owner validated v0.7.1 captured-area ground/air; the new workshop needs owner
Windows testing. These are normalized-world/native adapter tests. Live THUG
control of the Skate3Recomp guest remains pending.

SHA256: `90f9ca3ceb25986ff5b008bfa5c25bd5e8820bd172cc5e5b7753588e5f8ab2d4`

Code and tools only. ISO, retail captures and imported worlds stay on your PC.
Previous v0.6.6, v0.7.0 and v0.7.1 packages are preserved in this branch.
Source and project history are on [main](https://github.com/j2rsps-max/gonkskate/tree/main).

## Integration and character development check

[Download the engine/animated-character development check](https://raw.githubusercontent.com/j2rsps-max/gonkskate/downloads/GonkSkate-Integration-Check-829425e.zip) — 1.7 MB, source `829425e`.

Extract this into a **new folder** and run `RUN_INTEGRATION_CHECK.cmd`. Python
3.10+ is required. Return `logs/GonkSkate-integration-results-TIMESTAMP.zip`.
This console check runs authentic THUG through the new embeddable DLL and
verifies ground/air/rail replay against the existing executable. Keep the
v0.8.0 package for playable workshop testing.

Run `RUN_CHARACTER_CHECK.cmd` for 21 asset-free skeleton/mesh/animation/export tests.
It produces `logs/GonkSkate-character-results-TIMESTAMP.zip`. To import a
matching local THUG PC skeleton and skin:

```powershell
.\RUN_CHARACTER_CHECK.cmd "C:\path\to\character.ske.xbx" "C:\path\to\character.skin.xbx" --weight-profile dx9
```

The result is a local rigged, untextured GLB plus original metadata
under `local-characters/`. Use `--weight-profile xbox` for the inspected original
Xbox decoder. Extensions alone do not verify compatibility. The importer checks
joint ranges but cannot establish that two files are the correct asset pair.
Read `docs/CHARACTER_IMPORT_PROGRESS.md` for supported profiles and viewer checks.
To animate the rig with a matching original full skeletal clip:

```powershell
.\RUN_CHARACTER_CHECK.cmd "C:\path\to\character.ske.xbx" "C:\path\to\character.skin.xbx" --weight-profile dx9 --animation "C:\path\to\skater_Push.ska.xbx"
```

Select **THUG local clip** in your GLB viewer/editor's animation controls.
Compressed clips may need the matching local `--q-table` and/or `--t-table`
files (2048 bytes each). The importer reports missing tables; it rejects
unsupported partial overlays, events and camera/object clips.
Preview samples use original THUG math at 60 Hz with STEP interpolation.
If a viewer resamples animation, retain 60 Hz. Clip and rig bone counts must
match; indexed tracks cannot prove the correct rig identity. Textures, retail
appearance, gameplay animation selection and playable character attachment
remain pending. No retail or derived character assets enter download/results ZIPs.

Original Windows C++ reader fixtures match 26 synthetic files/390 vertices.
Both weight profiles and strip conversion match upstream. Four rigged GLBs
pass Khronos validation with zero errors/warnings and actual engine import/posed
skinning, including a rotated 63-bone hierarchy. Extracted-package format checks,
Unicode-path local synthetic imports, diagnostics and native replay also pass.
Original animation readers and complete pose samplers match 27 synthetic clips,
4156 decoded keys and 8128 poses. Five animated GLBs pass Khronos validation
with zero errors/warnings and actual engine playback/weighted deformation.

The ZIP also includes a logged Windows source-build helper for linking THUG
into the Skate frontend, with reuse of hash-verified installed TU3 patches.
Read `docs/THUG_EMBEDDED_RUNTIME.md`. The library/MSVC-ABI and native replay
tests passed under Wine; full retail source-build and live Skate player control
still need owner-side validation and player/tick/collision investigation.

SHA256: `c9d1e0a6fa2b12322298ec76eaa947a1aae9cd57bb219cedfa2f78822247184d`

The [previous geometry check](https://raw.githubusercontent.com/j2rsps-max/gonkskate/downloads/GonkSkate-Integration-Check-cc1e549.zip)
and [skeleton-only check](https://raw.githubusercontent.com/j2rsps-max/gonkskate/downloads/GonkSkate-Integration-Check-c390904.zip) are preserved.
