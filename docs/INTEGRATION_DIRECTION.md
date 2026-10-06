# Skate3Recomp as the main playable application

Decision accepted on 2026-10-05: build GonkSkate's gameplay/world integration
into Skate3Recomp, preserving its presentation and original Skate gameplay.
Add authentic THUG skating as an alternate gameplay mode. The Godot courtyard
remains a small regression harness for the native THUG adapter.

Only one skating backend controls a player at once. Having both implementations
available does not make their simulations interchangeable automatically. Switching
will need explicit ownership of input, collision, timing and player state. The
initial implementation should reset to a known spawn on mode changes rather
than assume both engines share identical internal state.

The THUG core and tested adapters remain cumulative. Keep the authentic C++
gameplay code and its normal Update ordering. Rust common/tooling work remains
useful; linking all physics into Rust is not a prerequisite for a native Skate
frontend. Do not expand the standalone prototype into a replacement game.

## Shared world import

Use source-specific converters behind one import command. Each converter emits
validated geometry, spawns and available skating metadata. Add visual materials,
collision materials/flags, rails, vert properties and provenance as they become
understood. Both gameplay modes should consume the same selected world through
their appropriate environmental adapters.

The current schema-1 inch/THUG-flag world is a tested bring-up profile, not a
finished universal asset specification. Preserve source metadata instead of
silently pretending every game uses THUG terrain IDs. Rendering an imported mesh
inside Skate3Recomp will not establish that its original Skate collision world
uses that mesh; the guest collision coupling remains a separate integration task.

Current unified CLI in `tools/import_map.py` supports triangulated OBJ, existing
normalized JSON and Skate3Recomp scene/buffer/memory-snapshot captures. Units are
explicit; output spawn overrides use inches and capture crop origins use meters.
Packed archives and proprietary game/mod formats currently have no decoder.

### Format priorities

| Source | Current support | Next prerequisite |
| --- | --- | --- |
| Neutral geometry | Triangulated OBJ and normalized world JSON | Visual materials and richer metadata; glTF/FBX require separate implementation |
| Skate 3 | Native render-capture importer, source-derived fixtures | Owner ground/air capture validated; original collision/rail research next |
| Tony Hawk games | No native level/archive importer yet | One THUG level collision import, then identify differences between games/platforms |
| THUG Pro maps/mods | No package decoder yet | Inspect actual mod files and THUG2-derived extensions; do not assume every THUG format matches |
| Skate 1/2 or Skate 3 mods | No general package decoder yet | Inspect representative files and supported source exports |
| Session maps/mods | Research candidate | Identify package/export formats, versions, collision and placement data |
| Skater XL maps/mods | Research candidate | Identify package/export formats, versions, collision and placement data |

An exported OBJ can enter the neutral importer regardless of where its author
made it. That does not establish direct support for that game's packaged mods.
Some mods may require an author export or conversion step. Import only data;
game-specific scripts, shader effects and gameplay logic do not become portable
by copying meshes. Use locally supplied assets; release code/tooling and avoid
publishing retail-derived worlds or character assets.

## Next integration checks

1. Retail scenery capture and real THUG ground/air have owner validation.
   Test workshop-authored rails on the same local world; continue original
   collision/rail research. This remains adapter verification tooling.
2. Prepare source-built Skate integration against pinned upstream. Preserve the
   original Skate controller/gameplay path as the default.
3. Identify and trace the guest player transform, physics update/scheduler and
   collision world. Renderer frame-end hooks are not proof of simulation timing.
4. Connect the THUG adapter to the selected world and main frontend, with
   explicit timing/input ownership. Test movement, landing and mode transitions.
5. Import one authentic Tony Hawk collision area. Broader formats follow these
   working engine/world boundaries rather than delaying their proof.

Development source now stages tested read-only presentation hooks into pinned
Skate3Recomp; see [the guest probe checkpoint](SKATE3_GUEST_PROBE.md). A full
source-built retail guest and gameplay switch have not yet been validated.
The owner's successful courtyard run validates the standalone THUG side,
not the live guest hooks or retail imports. Current pins and test evidence are
in SKATE3_DRIVER_INTEGRATION.md, SKATE3_WORLD_IMPORT.md and WINDOWS_VALIDATION.md.
