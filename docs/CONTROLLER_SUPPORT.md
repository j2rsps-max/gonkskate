# Controller support is required for both backends

v0.6.2 improves the THUG playable preview. Xbox-style controls are X push,
A crouch/release ollie, Y grind, left stick steer/brake, Start pause/resume and
Back reset. D-pad left/right/down also steer/brake. Keyboard Enter resumes or
pauses. Disconnecting the active controller pauses the simulation; reconnect
and press Start (or Enter) to resume. The current client selects the first
connected controller; explicit device selection is pending.

On PlayStation layouts these face positions correspond to Square, Cross and
Triangle. Physical Xbox/PlayStation USB/wireless compatibility still needs
Windows testing; cloud tests use synthetic Godot controller events.

`playable/controller_bindings.json` contains THUG action-to-Godot-button mappings,
stick deadzone and direction/brake thresholds. Restart the preview after editing.
Button IDs follow Godot's standard gamepad enum. An in-game remapping/calibration
UI and per-device saved profiles remain pending. Deadzones apply radially and
rescale the remaining stick range; triggers retain their independent 0–1 values.

Both raw and deadzone-filtered sticks, both triggers and the button mask are recorded in
`logs/playable-*.csv.controller.jsonl`. The launcher bundles these with native
CSV and diagnostics. The original THUG core currently reads directional button
states, so its movement adapter retains digital steering instead of inventing
an analog physics response. Right-stick and trigger data are captured but do not
control tricks/camera yet. Skate's eventual adapter must preserve its own
controller semantics, including Flick-It; the authentic input boundary is still
unknown. Controller support for Skate has not been implemented by this release.

## Test

Run normal interactive play with `RUN_PLAYABLE.cmd`. For simulated controller
push, crouch/release ollie, grind and pause/resume through original THUG physics:

```powershell
.\RUN_PLAYABLE.cmd --controller-autotest
```

This test injects Godot joypad events, runs 360 native ticks with 49 rail ticks,
and verifies that pause suspends five native ticks. It uses configured buttons.
The launcher also checks deadzone drift, radial magnitude, independent sticks
and triggers, remapping, pause/reset edges and simulated device discovery/loss.
These checks do not replace real hardware testing.

Return `logs\GonkSkate-playable-results-*.zip` after testing your controller.
Include its model and whether it was connected over USB or wireless.
