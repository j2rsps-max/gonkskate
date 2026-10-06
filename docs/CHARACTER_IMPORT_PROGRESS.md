# Character import progress

Character appearance remains independent from the map and physics backend.
The first combined Skate milestone will reuse its existing skater presentation
and customization. Tony Hawk guest/hidden characters and Skate 1–3/modded
characters remain goals; no universal character format compatibility is claimed.

The character pipeline now pairs **THUG v2 little-endian SKE skeletons** with
the inspected **Xbox/DX9 little-endian skin stream layout**. It exports a local
rigged GLB in the neutral pose and preserves original geometry, weight words,
bone indices, material/texture references, UVs, colors and LOD strips in a local
character package. Textures and animations are not imported yet, and this does
not add a playable character to Skate3Recomp.

## Owner check

The integration development ZIP includes **RUN_CHARACTER_CHECK.cmd**. With no
arguments it runs asset-free format/export checks and creates a diagnostic ZIP.
No native build tools, ISO or Godot install are required; Python 3.10+ is enough.

For a matching pair from your local THUG PC files:

```powershell
.\RUN_CHARACTER_CHECK.cmd "C:\path\to\character.ske.xbx" "C:\path\to\character.skin.xbx" --weight-profile dx9
```

For original Xbox decoder behavior, use `--weight-profile xbox` instead. The
profile must be explicit: the Xbox positive NORMPACKED3 decode divides by
1023/1023/511, while the inspected DX9 signed decoder divides by 1024/1024/512.
The extension alone does not select the platform or verify the stream layout.

Successful imports create `local-characters/thug-character-TIMESTAMP/` containing
`character.glb` and `character.json`. Open the GLB in a compatible viewer/editor
to check body shape, scale and bone placement. It has neutral surfaces and its
original rig; source textures, shader effects and animation are still pending.
Return **logs/GonkSkate-character-results-TIMESTAMP.zip**, even on failure.
The ZIP contains counts, hashes and test diagnostics; character geometry,
rig matrices, original files and the GLB stay local. Old imports are preserved.

The mesh stores numeric joint indices, not skeleton checksum IDs. The importer
rejects out-of-range influences but cannot prove that two files with compatible
bone counts are the correct pair. The original appearance/profile asset
selection still needs validation. Successful parsing alone does not establish
retail appearance fidelity or support for another Tony Hawk game's characters.

Repository command for a new output directory:

```powershell
python tools/import_thug_character.py "C:\path\to\character.ske.xbx" "C:\path\to\character.skin.xbx" --weight-profile dx9 --output local-characters\my-character
```

## Skeleton component

The skeleton-only tool reads **THUG v2 little-endian SKE skeletons**
from locally supplied files. It preserves bone/parent/flip checksum IDs, source
quaternions/translations, neutral local/world transforms and inverse bind matrices.
Normalized matrices use meters, row-major arrays and column-vector affine math.
Unknown bone names remain IDs rather than receiving guessed anatomical labels.

```powershell
python tools/import_thug_rig.py 'C:\path\to\character.ske.xbx' --output 'local-characters\character.rig.json'
```

Output must be new. Input extension alone does not establish format support.
This command imports only the skeleton. Its component JSON marks mesh and
animation import as false. The paired importer above adds geometry and skin
weights at package level. Raw files and derived characters stay local and are
excluded from development/results ZIPs.

## Source evidence

Inspected kisak-thug pin: `98b4e24921446ccd4b157453e25697f9574f0053`.

| Source | Basis for the importer |
| --- | --- |
| `Code/Gfx/Skeleton.cpp`, `CSkeletonData::Load(uint32*, int, bool)` | Header, three checksum tables, quaternion/vector rest poses, parent composition and inverse neutral matrices |
| `Code/Gfx/Pose.h`, `vMAX_BONES` | Loader asserts fewer than 64 bones |
| `Code/Core/Math/quat.inl`, `QuatVecToMatrix()` | Quaternion conjugation, row-vector source convention and float operation order |
| `Code/Core/Math/matrix.inl`, `InvertUniform()` and multiplication | Original parent/inverse-bind arithmetic |

Supported binary size is exactly `12 + 44 * bone_count`, with 1–63 bones.
The tool validates hierarchy order, unique IDs, known parent/flip IDs, finite
poses and normalized quaternions. It restricts the source version to 2 because
later formats have not been checked. It imports the buffer's flags; filename
special cases (`ped_f`), original bone-skip LOD scripts and skater appearance
profiles are not applied.

Float32 arithmetic matches the original scalar loader instead of allowing
Python doubles to accumulate different parent transforms. The differential
fixture compiles the original `CSkeletonData` class/methods and math against 40
synthetic skeletons with 830 total bones, including rotations, varied parent
chains and the 63-bone boundary. Maximum normalized inverse-matrix difference
was `1.27e-8` (native output is printed to nine significant digits). Five parser
tests also cover hierarchy/unit/rotation behavior and malformed input.

```bash
python3 tools/test_thug_rig.py
python3 tools/test_thug_rig_upstream.py
```

## Mesh, weights and GLB evidence

| Source at the same THUG pin | Implementation basis |
| --- | --- |
| `Code/Gfx/XBox/p_nx.cpp`, `s_plat_load_scene_from_memory()` | Three version words, materials, sector count and hierarchy tail |
| `Code/Gfx/XBox/p_nxsector.cpp`, `LoadFromMemory()` | Separate attribute streams, mesh records and 1–8 LOD strip sets |
| `Code/Gfx/XBox/NX/material.cpp`, `LoadMaterialsFromMemory()` | Descriptor layout and optional UV/color/texture animation records |
| `Code/Gfx/XBox/NX/mesh.cpp`, `Initialize()` | Packed weights and four uint16 source bone indices; shader register offsets are generated later |
| `Code/Gfx/XBox/NX/instance.cpp`, `RenderShadowVolume()` | Positive Xbox weight decoding |
| `Code/Gfx/DX9/NX/mesh.cpp`, `Initialize()` and strip conversion | Explicit signed PC decoder and strip parity through degenerate connectors |

The original scene loader reads but does not interpret its three version words.
We preserve them as unverified metadata; no retail version numbers have been
invented. Counts, lengths, finite values, referenced materials, joint ranges
and packed-weight quantization are checked. The first character profile rejects
negative weights, billboards, shadow-volume sectors, rigid attachments and
nonempty rigid hierarchies rather than guessing their placement.

The GLB keeps source axes, converts inches to meters, exports original bone
hierarchy/inverse-bind matrices, and emits highest-detail triangle lists. It
preserves all LOD strips and material records in the companion JSON. Weights
and normals are normalized **only for the GLB preview**; source values remain
intact. Inactive joint slots use valid zero IDs in the preview while the raw
sentinel indices remain in JSON. Double-sided neutral materials make missing
texture/effect reproduction explicit. This is geometry/rig interchange, not a
replacement for original shaders or appearance scripts.

Validation executes the exact original material/sector read bodies on Windows
x64 under Wine, with allocation/renderer capture facades and the original
32-bit `unsigned long` file data model. Across 26 synthetic files and 390
vertices, consumed offsets and attribute/LOD streams match. Both original
weight decoders and the original strip-conversion loop match as well. The
facades do not execute D3D rendering or procedural grass generation.

Duplicate zero-checksum dummy materials follow the original dictionary's
first-entry behavior while all records are preserved. Nonzero duplicate IDs
are rejected, matching the original loader. The 63-bone export test covers
the skeleton-loader limit; the original Xbox shader separately caps its
uploaded palette at 55 matrices, which is not exercised by this GLB fixture.

Four exported GLBs pass Khronos glTF validation with **zero errors and warnings**.
Godot's actual GLTF importer preserves geometry, checksum bone names and bind
matrices for both profiles, including a rotated 63-bone parent chain. Imported
bone movement deforms influenced vertices while the root-only vertex stays
fixed. The engine stores weights as UNORM16; maximum neutral-pose drift is
`1.87e-5` meters, within the measured rounding bound. The GLB itself keeps
float32 normalized weights. This engine use is a format-validation fixture;
Skate3Recomp remains the intended frontend.

```bash
python3 tools/test_thug_character.py
python3 tools/test_character_check.py
python3 tools/test_thug_skin_upstream.py --runner /path/to/wine64
python3 tools/test_character_preview.py --godot /path/to/godot --gltf-validator /path/to/gltf-validator-module
```

The differential helper currently uses the cloud Clang/MinGW toolchain. The
optional Khronos validator is a separately installed development dependency;
the owner check does not need it.

For the optional cloud validator, a reproducible installation is:

```bash
npm install --cache /tmp/gonk-npm-cache --prefix /workspace/tooling/gltf-validator gltf-validator@2.0.0-dev.3.10 --ignore-scripts --no-audit --no-fund
```

No retail skeleton or complete retail character has been validated here yet.
Next: validate one owner-supplied pair, decode its texture dictionary and original
animation clips, and then attach the character to the frontend. Spider-Man and
other THPS/Skate guest characters need their particular game/platform formats
verified before cross-game retargeting or selector support is claimed.
