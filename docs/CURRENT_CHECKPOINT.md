# GonkSkate checkpoint — 2026-10-07

The target application is **Skate3Recomp with selectable authentic THUG gameplay**.
Map, skater appearance and skating backend remain independent. One backend owns
the player's simulation at a time. The standalone courtyard/workshop remains a
regression and map-preparation tool.

## Which package to use

| Package | Purpose | Start it with |
| --- | --- | --- |
| v0.8.0 Windows Playable Full Package | Skate capture, map library, rail/spawn workshop and standalone real THUG play | `GONKSKATE.cmd` |
| Integration Check development package | Embedded THUG DLL checks and local rig/mesh/texture/animation import | `RUN_INTEGRATION_CHECK.cmd` or `RUN_CHARACTER_IMPORT.cmd` |

The [downloads page](https://github.com/j2rsps-max/gonkskate/tree/downloads)
links both packages and their hashes. Keep old working ZIPs and extract a
development check into a new folder. The development ZIP does not include
`GONKSKATE.cmd`, Godot or a new combined-game playable build.

## Owner PC layout and Codex continuation

The owner reports THUG is now installed under **`Z:\Games\GonkSkate`**, inside
its existing Tony Hawk's Underground subfolder. Its exact child name and file
layout have not been inspected by the cloud agent. Keep the game in place.
Use these separate siblings for the project:

```text
Z:\Games\GonkSkate\
  existing THUG game folder\
  Source\        full Git checkout for local Codex development
  Integration\   contents of the Integration Check package
  Playable\      contents of the v0.8.0 playable package
```

Put each package's contents directly in its chosen folder, so its `.cmd` files
are directly inside `Integration` or `Playable`. Keep earlier working imports
and logs; do not overwrite a nonempty development folder during a new extraction.
For an update, use another development folder or retain the previous folder first.

For the first file inventory with this layout:

```powershell
Set-Location -LiteralPath 'Z:\Games\GonkSkate\Integration'
.\RUN_THUG_FILE_CHECK.cmd
```

Browse to the **actual existing THUG subfolder**, then return
`logs\GonkSkate-thug-files-results-*.zip`. The scan reads names and sizes only,
skips GonkSkate packages and links, and reports incomplete scans. A filename is
a format hint, not evidence of a compatible rig/mesh pair.

For a new Codex conversation, use the root-level
[CODEX_START_PROMPT.txt](../CODEX_START_PROMPT.txt) and
[CODEX_HANDOFF.md](../CODEX_HANDOFF.md). Local Codex uses `Source` and the local
game installations; cloud Codex uses the same GitHub repository and asset-free
checks. The small development package is not the full source checkout.

## Evidence we already have

| Area | Confirmed result | Remaining boundary |
| --- | --- | --- |
| Authentic THUG movement | Original core/state/rotation code runs at 60 Hz with ground/air, ollie/landing, rail acquisition and grind movement; deterministic executable/library comparisons pass | Full trick, balance, scoring and bail behavior |
| Owner controller/play test | Courtyard run used ground/air/rail states and controller input; Windows session replay matched all 2,234 Linux ticks | Workshop controller authoring, physical hotplug and broader device coverage |
| Skate captured area | Later v0.7.1 owner run imported 857 triangles and completed 1,308 ticks with 12 landings and no native stops | Original collision/material/rail metadata; the earlier problematic area was not replayed |
| Character formats | Owner Windows logs confirm 26/26 synthetic rig/mesh/texture/animation/export checks passed | A matching retail asset set and visual inspection |
| Character preview | Original-source differential fixtures and actual-engine GLB tests pass for rigging, clip playback and first-pass textures | Original multipass shaders, appearance scripts and gameplay animation selection |
| Main frontend | Embedded THUG DLL, ABI handshake, input-driver code and read-only guest presentation probes are prepared and fixture-tested | Full retail source-build validation, controlled-player ownership, physics scheduler and collision coupling |

The failed owner character run had the same 26 passing format tests, followed by
a missing example file path. It revealed no decoder failure. No real character
has been imported on the owner's PC yet, and the file picker still needs its
first owner Windows run.

Evidence details are in [Windows validation](WINDOWS_VALIDATION.md),
[character import progress](CHARACTER_IMPORT_PROGRESS.md),
[embedded runtime](THUG_EMBEDDED_RUNTIME.md) and
[Skate guest probe](SKATE3_GUEST_PROBE.md).

## First real THUG import

The current THUG physics tests already run without retail assets. The completed
THUG installation/extraction supplies local character and map data for the next
import milestone. An ISO, installer or partially downloaded archive is not a
character source accepted by the picker.

1. Use the installed/extracted game's actual files. The inspected importer
   supports THUG little-endian Xbox/DX9 profiles; another game or platform needs
   separate verification. A `.xbx` suffix alone does not establish compatibility.
2. If you do not know which sources to select, run `RUN_THUG_FILE_CHECK.cmd`
   first and return its metadata-only results ZIP. Otherwise, in the Integration
   Check folder, run:

   ```powershell
   .\RUN_CHARACTER_IMPORT.cmd
   ```

3. Browse for a skeleton and its matching weighted mesh. Choose **THUG PC / DX9**
   for PC source files or **Original Xbox** for Xbox sources. Start with just this
   pair. Textures and animation can be added after the neutral body is correct.
4. A successful import writes `local-characters/thug-character-TIMESTAMP/` with
   `character.glb` and `character.json`. In a GLB-capable viewer/editor, check body
   shape, orientation, scale and missing pieces. This is an import preview;
   it does not register a character in the Skate frontend.
5. Repeat with the matching texture dictionary, then an original full skeletal
   clip if available. Select **THUG local clip** in the viewer. Compressed clips
   may require their matching Q48/T48 tables; the importer reports that explicitly.
6. Return the generated `logs/GonkSkate-character-results-*.zip` plus a brief
   description of the appearance. Keep the original files and derived GLB local.
   Return the same results ZIP if importing fails.

The asset-free character check already passed on Windows; there is no need to
repeat it before the asset inventory. `RUN_INTEGRATION_CHECK.cmd` remains a separate
optional DLL/replay check, requiring no game files.

## If the files are inside archives

Skeleton, mesh, texture and animation inputs commonly use `.ske`, `.skin`, `.tex`
and `.ska`, sometimes with a platform suffix. Choose actual files, not sample
`C:\path\...` strings. Matching bone counts do not prove a correct asset pair.
Some characters may assemble several body parts; one mesh is not guaranteed to
be a complete skater.

The character importer currently has no general game-archive extractor. If the
installation contains only packed data, first identify its actual format rather
than renaming an archive to `.skin` or selecting an unrelated file.

Use the folder inventory described above to identify source and archive names.
It does not copy or decode assets. A zero-match inventory
does not prove the installation is unsupported; it may use another archive
format. An incomplete download cannot establish file compatibility.

## Next engineering gates

1. Validate one owner-supplied THUG rig/mesh set; add its textures and full clip,
   then implement any demonstrated archive or format gap.
2. Complete the local source-built Skate frontend and verify ordinary Skate
   controller behavior before enabling the read-only presentation probe.
3. Establish controlled-player identity, authoritative simulation scheduling and
   original collision ownership. Presentation/animation hooks are observations,
   not an established physics boundary.
4. Attach the real THUG runtime with explicit input/time/world ownership and
   prove movement, landing, camera following and controlled backend switching.
5. Import one authentic THUG collision area. Broader maps and guest characters
   follow verified source formats and rig compatibility.

Retail import failures and frontend integration failures remain separate tasks.
A textured animated preview helps character interchange; the live combined-game
milestone still needs the player, tick and collision boundaries above.
