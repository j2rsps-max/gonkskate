# GonkSkate Windows download

This branch provides the prebuilt v0.6.6 Windows package. Source and development
history are on [main](https://github.com/j2rsps-max/gonkskate/tree/main).

[Download the full Windows ZIP](https://raw.githubusercontent.com/j2rsps-max/gonkskate/downloads/GonkSkate-v0.6.6-Windows-Playable-Full-Package.zip)

- File: `GonkSkate-v0.6.6-Windows-Playable-Full-Package.zip`
- Size: 71,348,893 bytes
- SHA256: `6d3c49861ea42d5f9edcdeba2fd10091338e7509e7a73dea271610f5c5f2e9eb`
- Source commit: `a65f2017a48093716b51fe691c55230b5aecbbee`

Extract into a writable folder, open GonkSkate-v0.6.6, and run:

```powershell
.\RUN_PLAYABLE.cmd --world worlds\courtyard.json
```

Python 3 is required. Godot and the Windows native executables are included.
For the local Skate capture test, read `docs\SKATE3_WORLD_IMPORT.md` in the ZIP.
Native and scene checks pass under Wine; owner hardware and a retail Skate
capture still need validation. No retail game files or captures are bundled.
