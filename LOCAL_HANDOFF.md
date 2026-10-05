# Continue GonkSkate locally on Windows

This is the existing cumulative project, currently v0.6.6. Do not recreate it.
Source and history are published on `j2rsps-max/gonkskate`'s `main` branch.
The separate `downloads` branch contains the verified Windows full package.
GitHub publishing works; the Codex cloud file-download UI was failing for the owner.

## Local checkout with prepared Windows tools

From PowerShell, choose a new project directory. The example uses your user
profile's `source\gonkskate` directory. If it already exists, use that checkout
or choose another directory; do not overwrite local work.

```powershell
git clone --single-branch --branch main https://github.com/j2rsps-max/gonkskate.git "$env:USERPROFILE\source\gonkskate"
cd "$env:USERPROFILE\source\gonkskate"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
```

The helper downloads the GitHub ZIP, checks its SHA256 and copies only the
prepared native executables/manifests and Godot into ignored build/bin directories.
It preserves source, configuration, saves and game files. Python 3 is required
to launch the preview. The helper is prepared for Windows; it has not been run
on the owner's hardware. Download/unpack failures leave a log and temporary files
for diagnosis rather than deleting an existing project.

Alternatively, download the full Windows package from the `downloads` branch
and extract it. That gives all source/tools/history too, but not `.git` metadata.

Open your local project folder in Codex desktop and start a new **local** task.
This cloud conversation cannot switch its execution host to the owner's PC.
An ordinary ChatGPT chat can advise, but PC file editing/builds need local Codex
or the owner running commands. Paste this prompt in the new local task:

> Continue this existing GonkSkate project as technical lead. Read
> LOCAL_HANDOFF.md, START_HERE.md, docs/SKATE3_WORLD_IMPORT.md, TEST_NOTES.md
> and docs/ROADMAP.md, then inspect the native adapters and Rust crates.
> Preserve authentic THUG physics and controller support. Run the courtyard
> test, find my working Skate3Recomp installation in Downloads, verify its
> version/capture support, and test real THUG skating on locally captured Skate
> scenery. Investigate failures and modify/build/test the project. Keep me
> informed and commit meaningful changes to my GitHub repository. Do not
> upload retail game assets, memory captures or imported retail geometry.

## Current engineering state

- Authentic THUG core `Update`, state, rotation, math, input and rail manager
  execute outside the rendered game loop at deterministic 60 Hz. Ground/air,
  ollies, landing and basic rail movement work in the standalone profile.
- The Godot client supplies controller/keyboard input and draws authoritative
  native state. Runtime world files provide shared float32 geometry, spawn,
  facing and multiple rail chains. Rust's selectable simulation backends are
  still placeholders; the whole runtime is not yet linked as Rust handles.
- The Skate adapter uses the real ReXGlue input interfaces; its encoder/driver
  tests pass. It is not attached to a running retail guest. Skate player,
  scheduler and collision-world boundaries remain unresolved.
- Local OBJ and Skate scene/buffer/Windows-memory-snapshot importers exist.
  Synthetic source-format fixtures pass through real THUG push/ollie/landing.
  **No retail Skate capture has been validated yet.** That is the next milestone.
- Retail import currently uses visible render triangles, generic concrete and
  a procedural skater. Original Skate collision, textures, materials, rails,
  characters and gameplay are absent. Unsupported THUG peripherals fail fast.
- Native rebuild scripts currently use Linux/Clang and a MinGW cross-toolchain.
  Use the packaged Windows binaries initially. Native C++ changes will need
  a local build-toolchain setup/port or WSL; Visual Studio detection alone does
  not establish that these particular build helpers work on Windows.

Validation already passed in the cloud: Rust workspace, native ABI/parameters,
stat differential, 10,000 THUG ticks/55 landings, 49 rail ticks, deterministic
replay, imported-world/reset/facing/malformed-data checks, 15,000 indexed-vs-linear
collision queries, controller and scene integration. Windows executables/scenes
were checked under Wine; actual hardware/controller and retail capture are unrun.

Pins: THUG `98b4e24921446ccd4b157453e25697f9574f0053`, Skate
`f6e0ae87fdfecbadb5c1e36c55d66a744187a3cd`, ReXGlue
`7eb0faf7787f5e01333c228b8e3f03c32f7295ea`. The prebuilt ZIP comes from source
commit `a65f2017a48093716b51fe691c55230b5aecbbee`; later local-setup/handoff
commits only add these transfer instructions and tooling.

## Owner context and immediate tests

Windows PC: RTX 2070 8 GB, Ryzen 3600X, 16 GB DDR4, 1080p. Working Skate3Recomp
and Xbox ISO are in Downloads. Its controller works well. Performance is a
secondary priority; first prove the combination. The owner wants useful progress
quickly and prefers active engineering over theoretical plans. Controller support
is required for both backends. THPS/THUG hidden characters, Skate 1–3 characters
and compatible modded characters are future appearance/import goals in ROADMAP.

```powershell
.\RUN_PLAYABLE.cmd --world worlds\courtyard.json
# Close the existing Skate3Recomp window; substitute its actual executable path.
.\RUN_SKATE3_CAPTURE.cmd --exe "C:\Users\YOUR_NAME\Downloads\Skate3Recomp\skate3.exe"
```

Enter a level, stop on open flat ground, press F10 once, wait for capture to
finish, then quit normally. The helper imports the area and launches THUG
skating. The installed Skate release must include capture diagnostics (target
pin is v2.0.0); verify rather than assume the owner's version.

Return asset-free `logs\GonkSkate-skate3-capture-results-*.zip` and
`logs\GonkSkate-playable-results-*.zip`. ISO, captures and `local-worlds` stay
local and ignored. The old history packages and PowerShell 5.1 exit-code/stderr
and `$Args` fixes must remain intact. Continue versioning from v0.6.6.
