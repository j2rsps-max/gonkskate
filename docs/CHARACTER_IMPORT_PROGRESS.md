# Character import progress

Character appearance remains independent from the map and physics backend.
The first combined Skate milestone will reuse its existing skater presentation
and customization. Tony Hawk guest/hidden characters and Skate 1–3/modded
characters remain goals; no universal character format compatibility is claimed.

The first implemented asset tool reads **THUG v2 little-endian SKE skeletons**
from locally supplied files. It preserves bone/parent/flip checksum IDs, source
quaternions/translations, neutral local/world transforms and inverse bind matrices.
Normalized matrices use meters, row-major arrays and column-vector affine math.
Unknown bone names remain IDs rather than receiving guessed anatomical labels.

```powershell
python tools/import_thug_rig.py 'C:\path\to\character.ske.xbx' --output 'local-characters\character.rig.json'
```

Output must be new. Input extension alone does not establish format support.
Meshes, materials/textures, skin weights, animations, retargeting and a playable
character selector are separate work. The JSON marks those imports and retail
validation as false. Raw skeleton files and derived rigs stay local and are
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

This validates the source-format implementation; no retail skeleton or complete
retail character has been imported here yet. Next: check one owner-supplied rig,
decode its matching THUG skin mesh/materials, and preserve its original animation
rig before considering cross-game retargeting. Spider-Man support depends on the
specific source game's model/rig/animation formats, not its character name.
