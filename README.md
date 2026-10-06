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

[Download the engine/rig development check](https://raw.githubusercontent.com/j2rsps-max/gonkskate/downloads/GonkSkate-Integration-Check-c390904.zip) — 1.7 MB, source `c390904`.

Extract this into a **new folder** and run `RUN_INTEGRATION_CHECK.cmd`. Python
3.10+ is required. Return `logs/GonkSkate-integration-results-TIMESTAMP.zip`.
This console check runs authentic THUG through the new embeddable DLL and
verifies ground/air/rail replay against the existing executable. Keep the
v0.8.0 package for playable workshop testing.

Optional: pass a local THUG SKE v2 little-endian skeleton to the command to
start its rig import. Derived rigs stay local; complete character meshes and
animations remain pending. No retail files are included in the download/results.

The ZIP also includes a logged Windows source-build helper for linking THUG
into the Skate frontend, with reuse of hash-verified installed TU3 patches.
Read `docs/THUG_EMBEDDED_RUNTIME.md`. The library/MSVC-ABI and native replay
tests passed under Wine; full retail source-build and live Skate player control
still need owner-side validation and player/tick/collision investigation.

SHA256: `bb4c392dce9483bbfcda13a357fb23105adcc11cb117fec6996c175cd373e0c0`
