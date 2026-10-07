# Owner Windows validation

## Character format checks — 2026-10-06

Two owner result ZIPs from the `5299504` development package each report all
26 synthetic rig/mesh/texture/animation/export checks passing. The `191638-282253`
run completed with exit code 0. The `191701-368144` run completed the same tests,
then returned exit code 1 for a nonexistent example skeleton path (WinError 3).
Both contain only `report.json` and `format-tests.txt`. No retail character was
imported, and the newer file picker has not yet run on the owner's Windows PC.

The [current checkpoint](CURRENT_CHECKPOINT.md) defines the next local asset test.

## Owner v0.7.1 capture and play

The next owner capture imported 857 render triangles at a 25 m radius. The
native world SHA256 was
`0e348029617b5a5f5305a37b0fa12a38cc81ff7ef7fd473da449551111cdb91f`.
The standing-ollie check passed again: 180 fixed ticks, 63.1982002 inch apex,
landing at frame 83 and exact replay.

Interactive play completed 1,308 native ticks: 982 ground, 326 air, 12 landing
flags, ten ollie events, three GroundGone events and one reset. Grind input was
held in 116 ticks, but the capture had zero rails and never entered RAIL. The
session-health report recorded no failures/recoveries; both capture and play
stages exited successfully. This is a different area from the earlier 5,415-face
capture, so it does not prove every earlier wall contact was retested.

The supplied ZIPs contain counts, identity and input/state traces, not retail
geometry. The v0.8.0 workshop and new controller authoring still require an owner
Windows test; Windows Godot and native executables have been exercised under Wine
using original synthetic geometry, including an editor-authored grind.

## First owner Skate capture — 2026-10-06

The v0.7.0 F10 capture/import workflow completed on the owner's PC and produced
5,415 render triangles. Its native world SHA256 was
`6d6975746e88c8c3328303843a07644acc45886f108bbaa9305966546f042982`.
The standing-ollie check passed: 180 fixed ticks, 63.2000122 inch apex, landing
at frame 83 and exact replay. The owner could skate around the captured area.
The live controller lab also passed with 475 physical input samples, independent
sticks and both triggers reaching 1.0.

Two interactive sessions stopped at native frames 604 and 569: an unidentified
self-event and an unimplemented bonk-sound call. The old window/launcher reported
exit 0 despite these stops. The captured world had zero rails, and those session
traces did not enter RAIL. v0.7.1 fixes the audited contact/event paths, failure
reporting and reset recovery. The later successful run used another area.
See [hotfix notes](V071_HOTFIX.md). The result ZIPs contain identity/trace data,
not the captured world, so retail geometry has not been replayed in the cloud.

## Original courtyard validation

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
