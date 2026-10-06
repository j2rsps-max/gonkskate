# v0.7.1: wall-contact stops and session recovery

The owner's first local Skate capture imported 5,415 render triangles and passed
the real THUG flat-spawn/standing-ollie/landing test with exact replay. Interactive
sessions then stopped at frame 569 in `PlayBonkSound` and frame 604 in an unknown
skater self-event. The v0.7.0 launcher incorrectly reported both sessions as
successful after the test window was closed. The returned traces contained no
rail-state frames; the captured world has zero rail annotations.

## Fix

The sound peer now records bonks without requesting an audio engine. Audited
`FlailLeft`, `FlailRight`, `GroundGone` and ground `WallPush` events explicitly
record unavailable animation, rumble and script trick/score presentation. The
original core still computes wall deflection, wall-push speed/direction, ground
loss, gravity and landing through its usual `Update()` ordering. No collision
response is replaced with host physics, and no unknown event is silently ignored.
Original balance/trick/animation handlers are not fully executed by this profile;
this remains a static-world bring-up, not a complete THUG gameplay implementation.

Unknown events retain the fail-fast behavior and now log their checksum and all
accumulated dependency counters. If a native stop occurs, Back/View or R starts
a fresh native skater at the selected world's spawn. Each segment receives its
own trace. Escape still works after failure. The session-health report retains
every failure and recovery; closing the window or resuming cannot turn a failed
session into a passed hub result.

The Unix launcher preserves ignored SIGPIPE so writes to a dead child produce a
recoverable pipe error. The client also retains EOF stderr pipes until shutdown
on Unix: Godot 4.4.1's `OS_Unix::execute_with_pipe` opens stderr with write fd 0,
and closing it immediately closes parent stdin and breaks a subsequent child.
Windows closes its stderr handle normally. This workaround affects process IO,
not simulation timing or physics.

## Reproduction and verification

Four original synthetic fixtures exercise ground bonks, airborne bonks with
grind held, ground wall-push with grind held, and leaving a raised ledge. The
v0.7.0 Windows executable stops in each case. The patched Linux and Windows
executables run all 360 ticks, preserve finite state, collision response,
landing/reset and identical replay. All four complete CSV traces match between
Linux and Windows under Wine. Existing ground/air/rail/ramp/10,000-tick and runtime
world tests pass. Godot fault-injection tests kill the real native child twice,
reset with simulated controller Back and keyboard R, resume native ticks, and
retain both failures. Those tests pass on Linux and Windows under Wine.

The actual captured world stays on the owner's PC and was absent from the result
ZIPs. These are equivalent failure-path reproductions, not a replay of the
specific retail geometry. The old self-event log did not identify its checksum,
so it does not establish which event fired at frame 604. Future stops provide it.

## Retest without another capture

Close the hub and test window. Copy the contents of the new `GonkSkate-v0.7.1`
package folder into the existing GonkSkate folder, replacing included files. The
package excludes `user/`, `local-worlds/` and raw capture folders; their contents
remain local. Keep the older ZIP for recovery.

1. Open `GONKSKATE.cmd` and run **Run milestone check**. It now includes all four
   contact/drop checks as well as the existing native and controller checks.
2. In **Map library**, select the same captured Skate area and **Play with THUG**.
3. Hit the old troublesome geometry on the ground and while airborne, hold Y/E
   near walls, ride off ledges, and reset. Captured render geometry may still have
   holes or unsuitable surfaces; the importer supplies generic concrete.
4. If physics stops, try Back/View or R, then finish with Escape. Return the newest
   `logs/GonkSkate-milestone-results-*.zip`, even if recovery succeeded.

Actual grinding still requires annotated rails. Use the courtyard to check rail
acquisition/grind/exit; pressing Y/E near unannotated Skate scenery can invoke
THUG wall actions, but cannot create a rail. Wallride/wallplant/full trick/bail
support and original Skate collision/material/rail import remain future work.
