# First owner Windows validation — 2026-10-05

The owner ran v0.6.6's courtyard interactively on Windows and reported that
controller input and gameplay worked well. The returned asset-free results ZIP
confirms exit code 0, Godot 4.4.1 and rendering on the RTX 2070. This was the
original synthetic OBJ courtyard, not a retail Skate capture.

The live session contains 2,234 matching native/input frames: 1,859 ground,
342 air and 33 rail frames, with nine landing flags and one reset. Push,
crouch, left/right steering, braking and grind inputs were exercised. Left-stick
input appeared in 904 frames and right-stick input in 113 frames. No unexpected
peripheral failure appeared in the live adapter report.

The native regression suite passed on the owner's machine: 10,000 ticks and
55 landings, 49 rail ticks, ramp contact, replay, steering, braking, reset and
intentional unsupported-call checks. The automated controller mapping/deadzone/
connection tests also passed; those tests simulate input rather than establishing
physical disconnect/reconnect behavior.

We encoded the same courtyard, verified its binary hash against the returned
run, and replayed all seven native input fields from the live Windows session
through the Linux executable. Every CSV line matched exactly across all 2,234
ticks. This supports deterministic replay for the exercised profile.

Report ZIP SHA256:
`d1d091b63d3d24ce90aad0028385a93559a8be1a7442b8865bf61daeaa5d17a9`.
Raw owner logs and controller traces stay outside the published repository.

This validates the current THUG courtyard/client/controller path. It does not
validate a retail Skate capture, original Skate physics inside GonkSkate, guest
player/scheduler integration, or all controllers and unsupported THUG states.

The gray Godot scene is an input/rendering regression harness. The skating
authority is authentic THUG code. Main-app presentation and the integration
strategy remain separate from this successful test; opening two game processes
does not connect their collision worlds or player simulations.
