# GonkSkate reference check v0.6.4

This small download uses your existing Skate3Recomp installation. Python 3 is
required. Extract the ZIP into a writable folder and keep Skate3Recomp open.

Run:

```powershell
.\RUN_SKATE3_REFERENCE.cmd --inspect-only
```

The checker finds one running `skate3.exe` on Windows, hashes the executable and
checks known extracted-game locations beside it and under AppData. The game stays
open. It does not transfer your ISO or copy retail files into the report.

Return `logs\GonkSkate-skate3-reference-results-*.zip`. Also report whether your
controller can steer, push, do right-stick ollies/kickflips and use both triggers.
Include its model, USB/wireless and any Steam Input use.

If automatic discovery fails or more than one instance is open, use the exact
executable path:

```powershell
.\RUN_SKATE3_REFERENCE.cmd --inspect-only --exe "D:\Skate3Recomp\skate3.exe"
```

Replace that example path with your installation. No game location found in the
report does not mean the game is broken; custom install paths may need a separate
game-root check using the full GonkSkate v0.6.3 controller-test package.

For a later console-logged reference run, first quit Skate normally and then run:

```powershell
.\RUN_SKATE3_REFERENCE.cmd --exe "D:\Skate3Recomp\skate3.exe"
```

Play, then quit normally to finish its result ZIP. This starts the separate
upstream game; it does not run Skate physics inside GonkSkate. Inspection-only
reports contain metadata rather than gameplay or console traces.
