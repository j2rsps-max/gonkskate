#pragma once
#include "gonkskate_thug_collision.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {GonkVec3 vertices[3];uint16_t flags,terrain;} GonkThugTriangle;
typedef struct {const GonkThugTriangle* triangles;uint32_t count;uint8_t floor;} GonkThugMeshWorld;
uint8_t gonk_thug_mesh_query(void*,const GonkThugCollisionQuery*,GonkThugCollisionHit*);
#ifdef __cplusplus
}
#endif
