# Character import progress

Character appearance remains independent from the map and physics backend.
The first combined Skate milestone will reuse its existing skater presentation
and customization. Tony Hawk guest/hidden characters and Skate 1–3/modded
characters remain goals; no universal character format compatibility is claimed.

The character pipeline now pairs **THUG v2 little-endian SKE skeletons** with
the inspected **Xbox/DX9 little-endian skin stream layout**. It exports a local
rigged GLB in the neutral pose, optionally with a matching original skeletal
animation clip, and preserves original geometry, weight words,
bone indices, material/texture references, UVs, colors and LOD strips in a local
character package. Textures and gameplay animation selection remain pending; this does
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
original rig; source textures and shader effects remain pending.
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

To preview a matching original full skeletal clip, append `--animation`:

```powershell
.\RUN_CHARACTER_CHECK.cmd "C:\path\to\character.ske.xbx" "C:\path\to\character.skin.xbx" --weight-profile dx9 --animation "C:\path\to\skater_Push.ska.xbx"
```

Select **THUG local clip** in your GLB viewer/editor's animation controls.
The example filename illustrates upstream's push-animation naming, not a
verified retail path or a guarantee that a particular clip matches your rig.
If a compressed clip reports a missing lookup table, append `--q-table` and/or
`--t-table` with the matching original local tables. Each contains 256
four-short entries (2048 bytes); do not substitute guessed defaults. Clips
whose compressed tracks use no table references need no table files.

Keep the original files, tables, `character.glb` and `character.json` on your PC.
Return only the results ZIP. Successful imports preserve all decoded source
keys in the local package; the diagnostic ZIP records only their hashes,
formats, duration and counts. A clip's indexed tracks must match the rig's
bone count. These ordinary skater clips contain no bone checksums, so a count
match cannot establish the correct rig identity.

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

## Original animation formats and pose math

The same upstream pin supplies the animation reader and sampling behavior:

| Source | Checked behavior |
| --- | --- |
| `Code/Gfx/BonedAnim.cpp`, `PostLoad()` and `plat_read_stream()` | Header, flags, per-bone byte/short counts, alignment and eight-byte platform keys |
| `plat_read_compressed_stream()` and `get_compressed_q_frame()` / `get_compressed_t_frame()` | Allocation/per-bone byte sizes, Q48/T48 lookups, short timestamps and unsigned byte rotation components |
| `GetInterpolatedFrames()` / `GetCompressedInterpolatedFrames()` | Inclusive key selection, 60 Hz timestamp conversion, last-key behavior and compressed negative-identity optimization |
| `Code/Core/Math/quat.inl`, `FastSlerp()` | Shortest-path normalized linear interpolation, including endpoint behavior |
| `Code/Gfx/Skeleton.cpp`, `sQuatVecToMatrix()` and `CSkeleton::Update()` | Absolute bone-local poses, parent composition and inverse-neutral skinning; poses are not added to the neutral pose |

Supported clips are little-endian full skeletal animations using platform short
keys or table-compressed short keys. Frame timestamps and prerotated-root flags
are required, matching the original loader. Its header version is recorded as
unverified because the original loader does not select layouts by that value.
High-resolution count tables are supported; high-resolution **key values**,
partial overlays, camera/object/cutscene profiles, old intermediate formats and
custom event keys are explicitly rejected. No unsupported event is silently
dropped. These events can change bone parents or create objects and need their
actual environmental adapters.

Bounds include 1–63 bones, 1–32767 total keys per stream, 16 MiB source files,
strictly increasing nonnegative track times, nonempty full tracks and finite
positive durations up to `16383 / 60` seconds. The preview allows at most one
million sampled bone poses. Truncation, allocation/count disagreements and
unexpected trailers fail before creating an import directory. The original
scan's unusual before-first-key behavior (selecting the last key) is preserved.

The reusable sampler performs the original float32 quaternion reconstruction,
translation scaling (`short / 32` inches), sign handling and interpolation.
The neutral rig's inverse bind matrices remain in the animated GLB. Poses use
original local transforms directly; root motion remains in the clip. Quaternion
XYZ conjugation converts the original row-vector matrices to GLB's column-vector
convention, and translations become meters. Appearance scaling, stance flips,
board adjustments, gameplay clip selection/blending and cross-rig retargeting
are not applied.

glTF's LINEAR quaternion channels specify spherical interpolation, which differs
from THUG's `FastSlerp`. The preview therefore bakes source samples at 60 Hz with
**STEP** channels, plus an exact-duration endpoint. Fractional preview times hold
the preceding sample; the reusable sampler retains the original fractional-time
behavior. Preview quaternions are normalized for glTF while raw decoded keys
remain unchanged. A viewer that resamples animation must retain 60 Hz: Godot's
default 30 Hz bake loses samples, so the validation explicitly requests 60 Hz.

The differential fixture executes the original `CBonedAnimFrameData` class,
loaders, key decoders, complete full-clip samplers, original `FastSlerp` and
original local skeleton-matrix function on Windows x64 under Wine. Across
**27 synthetic clips, 4156 decoded keys and 8128 bone poses**, platform and
compressed streams, sign/identity quirks, all seven byte-component combinations,
table indices above 127, wide count tables, quantization clamps, time boundaries
and varied rotations agree. Maximum printed quaternion difference is `4.85e-9`;
translation difference is `5.01e-8` inches. File I/O uses synthetic buffers;
custom events and hardware DMA are outside the supported fixture profile.

Five animated GLBs pass independent Khronos validation with **zero errors and
warnings**. Actual Godot AnimationPlayer seeking/playback preserves absolute
local transforms, STEP holds, reverse seeks and weighted deformation, including
a rotated 63-bone source rig. Maximum animated vertex difference is `8.57e-6`
meters in that long chain. This validates interchange/playback, not a live
Skate player, original rendering or retail animation compatibility.

```bash
python3 tools/test_thug_animation.py
python3 tools/test_thug_animation_upstream.py --runner /path/to/wine64
python3 tools/test_animation_preview.py --godot /path/to/godot --gltf-validator /path/to/gltf-validator-module
```

No retail skeleton, clip or complete retail character has been validated here yet.
Next: validate an owner-supplied rig/mesh/clip, decode its texture dictionary and
attach the character to the frontend. Spider-Man and
other THPS/Skate guest characters need their particular game/platform formats
verified before cross-game retargeting or selector support is claimed.
