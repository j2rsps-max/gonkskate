#pragma once
#include "gonkskate_thug.h"

#ifdef _WIN32
#ifdef GONK_THUG_RUNTIME_BUILD
#define GONK_THUG_RUNTIME_API __declspec(dllexport)
#else
#define GONK_THUG_RUNTIME_API __declspec(dllimport)
#endif
#else
#define GONK_THUG_RUNTIME_API __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
extern "C" {
#endif

/* Embeddable versioned API for the tested static-world ground/air/rail profile.
 * It uses original THUG Update ordering at exactly 60 Hz. Coordinates and
 * velocity are inches and inches/second. No renderer, character or variable
 * timestep is implied. One live session per process, used by its creator thread.
 * The earlier gonkskate_thug.h lifecycle declarations remain design-only. */
#define GONK_THUG_RUNTIME_ABI 1u
typedef uint64_t GonkThugRuntimeHandle;
enum GonkThugRuntimeStatus {
    GONK_RUNTIME_OK=0,GONK_RUNTIME_INVALID_ARGUMENT=1,GONK_RUNTIME_BUSY=2,
    GONK_RUNTIME_WRONG_THREAD=3,GONK_RUNTIME_UNSUPPORTED=4,GONK_RUNTIME_ASSERT=5,
    GONK_RUNTIME_FAILED=6,GONK_RUNTIME_INVALID_HANDLE=7,GONK_RUNTIME_ERROR=8,
    GONK_RUNTIME_ABI_MISMATCH=9
};
#define GONK_RUNTIME_TEST_AREA 1u
typedef struct {
    uint32_t abi_version,struct_size,flags,reserved;
    /* UTF-8 normalized .gonkworld path, copied during create; NULL means the
     * synthetic floor (or original test area when TEST_AREA is set). */
    const char* world_path;
} GonkThugRuntimeConfig;
typedef struct {
    uint8_t push,crouch,left,right,brake,grind;
    uint8_t reset,reserved; /* reset is 0/1; other controls are original pad pressure 0..255 */
} GonkThugRuntimeControls;
typedef struct {
    uint32_t abi_version,struct_size;
    uint64_t completed_ticks;
    GonkVec3 position,velocity,forward,up;
    /* Original THUG state ID; deliberately distinct from the design enum:
     * GROUND=0, AIR=1, WALL=2, LIP=3, RAIL=4, WALLPLANT=5. */
    int32_t native_state,terrain,rail_node;
    uint8_t landed_this_frame,reserved[3];
    uint64_t collision_queries,parameter_lookups,adapter_calls; /* last tick */
} GonkThugRuntimeState;
typedef struct {
    uint32_t status,reserved;
    uint64_t frame;
    char message[512];
} GonkThugRuntimeError;

GONK_THUG_RUNTIME_API uint32_t gonk_thug_runtime_abi_version(void);
GONK_THUG_RUNTIME_API int gonk_thug_runtime_create(const GonkThugRuntimeConfig*,GonkThugRuntimeHandle*);
GONK_THUG_RUNTIME_API int gonk_thug_runtime_destroy(GonkThugRuntimeHandle);
/* Exactly one authentic fixed tick. Failure invalidates further stepping;
 * destroy and create a fresh session before continuing. */
GONK_THUG_RUNTIME_API int gonk_thug_runtime_step(GonkThugRuntimeHandle,const GonkThugRuntimeControls*,GonkThugRuntimeState*,uint32_t state_size);
GONK_THUG_RUNTIME_API int gonk_thug_runtime_get_state(GonkThugRuntimeHandle,GonkThugRuntimeState*,uint32_t state_size);
/* Last error belongs to the calling thread; no exception crosses this ABI. */
GONK_THUG_RUNTIME_API int gonk_thug_runtime_get_error(GonkThugRuntimeError*,uint32_t error_size);
#ifdef __cplusplus
}
#endif
