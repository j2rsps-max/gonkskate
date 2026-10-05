#pragma once
#include "gonkskate_thug.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Versioned collision seam. THUG coordinates use inches, +Y up.
 * Flags/terrain here use THUG encodings; a normalized-world importer translates
 * its own material IDs at this boundary. No native object pointers cross it.
 */
#define GONK_THUG_COLLISION_ABI_VERSION 2
#define GONK_THUG_FACE_SKATABLE 1
#define GONK_THUG_TERRAIN_CONCRETE_SMOOTH 1
typedef struct {
    GonkVec3 start, end;
    uint16_t ignore_1, ignore_0;
    uint8_t farthest;
} GonkThugCollisionQuery;
typedef struct {
    GonkVec3 point, normal;
    float fraction;
    uint16_t flags, terrain;
    uint32_t node_name, script;
    uint8_t trigger, movable;
} GonkThugCollisionHit;
typedef struct {
    uint32_t abi_version;
    void* user;
    uint8_t (*query)(void* user,const GonkThugCollisionQuery*,GonkThugCollisionHit*);
} GonkThugCollisionApi;
/* Explicit two-sided mathematical plane; one possible normalized test world. */
uint8_t gonk_thug_flat_plane_query(void*,const GonkThugCollisionQuery*,GonkThugCollisionHit*);
#ifdef __cplusplus
}
#endif
