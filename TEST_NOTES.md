# Windows test pass

The owner's v0.6.6 courtyard/controller test passed on Windows. Its 2,234-frame
live trace replays exactly on Linux. See [verified results](docs/WINDOWS_VALIDATION.md).
Retail Skate capture and integration remain unvalidated.

v0.6.6 priority: follow [Skate world import](docs/SKATE3_WORLD_IMPORT.md).
First run `RUN_PLAYABLE.cmd --world worlds\courtyard.json`, then the local Skate
capture command. Return capture-results and playable-results ZIPs only.
The controller and reference checks below remain available.

v0.6.5 adds original-SDK host driver checks to `RUN_SKATE3_CHECK.cmd`:
`native-sdk-check.txt` must contain both `SKATE3_DRIVER_TEST passed` and
`SKATE3_INPUT_TEST passed`. These verify SDK input routing, not a retail guest run.

If Skate3Recomp is already working, first run `RUN_SKATE3_REFERENCE.cmd --inspect-only`
while its window is open. The v0.6.4 standalone reference-check ZIP needs only
Python 3 and records executable/game metadata. The full playable tests below
remain available in the full Windows preview package.

Extract the full package into a writable folder. Python 3 is required; Godot and
both native test executables are included. Old releases remain unchanged.

## 1. Hands-free checks

```powershell
.\RUN_PLAYABLE.cmd --controller-autotest
.\RUN_SKATE3_CHECK.cmd --autotest
```

These use simulated input. The first checks real THUG movement, grind,
pause/resume and right-stick camera look. The second checks the SDK packet bridge
and both stick/trigger channels, standard buttons and simulated reconnect.

## 2. Controller lab

```powershell
.\RUN_SKATE3_CHECK.cmd
```

Move both sticks in full circles, then let go to check center drift. Squeeze LT
and RT separately, then together. Press all face buttons, shoulders, stick clicks,
D-pad, Start and Back. Disconnect and reconnect once. Press Escape to finish.
This is a controller lab, not Skate gameplay. Check that left/right readings stay
independent and both triggers reach approximately 1.0.

If extracted Skate 3 Xbox 360 files are ready, run the same check with your path:

```powershell
.\RUN_SKATE3_CHECK.cmd --game-root "D:\Skate3Recomp\game"
```

Replace that example path with your actual game directory. This adds a metadata
and known-TU3 report; the ZIP contains no retail game files.

## 3. Playable THUG regression

```powershell
.\RUN_PLAYABLE.cmd
```

X pushes, A crouches/releases ollie, Y holds grind; left stick steers/brakes.
Right stick now orbits/raises the camera. Start pauses, Back resets. Ride the ramp,
grind the rail, ollie off it, then disconnect/reconnect the controller and resume
with Start. Escape quits. Keyboard controls remain W/A/D/S, Space, E and R.

## 4. Optional authentic Skate reference

For actual Skate gameplay today, install a release from
[Yoraikou/Skate3](https://github.com/Yoraikou/Skate3/releases), supply your own legally
obtained game through its installer, and then use your installed executable:

```powershell
.\RUN_SKATE3_REFERENCE.cmd --exe "D:\Skate3Recomp\skate3.exe"
```

This starts the separate upstream game and captures its console output. It does
not switch GonkSkate to Skate physics. Quit that game to finish the ZIP. For
PlayStation/generic controllers, upstream recommends selecting SDL in Settings
> Controls > Controller Backend and restarting; standard Xbox uses XInput.
Test push, steering, right-stick ollies/kickflips, both triggers and pause there.

## Return these files

Send the newest ZIP from each test you ran:

- `logs\GonkSkate-playable-results-*.zip`
- `logs\GonkSkate-skate3-check-results-*.zip`
- `logs\GonkSkate-skate3-reference-results-*.zip` (optional)

Include controller model, USB/wireless, any Steam Input use, and which action felt
wrong or did nothing. Do not send game assets or manually copy console output.

Cloud validation covers Rust/native tests, real THUG traces, Linux/Windows SDK
packet equality, the controller lab, and Windows scene tests under Wine. Actual
Windows hardware and the authentic Skate guest remain to be tested locally.

v0.6.5 validation: original-SDK driver routing checks pass on Linux and Windows
under Wine, including settings open/close and vibration filters. The 180-sample
controller-lab regression passes. The adapter CMake static-library compile check
uses upstream headers; it does not build or run the complete retail guest.
