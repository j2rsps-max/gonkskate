#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct GonkThugHandle GonkThugHandle;

typedef struct {
    float x;
    float y;
    float z;
} GonkVec3;

typedef struct {
    float left_x;
    float left_y;
    float right_x;
    float right_y;

    uint8_t ollie;
    uint8_t grind;
    uint8_t grab;
    uint8_t flip;
    uint8_t revert;
    uint8_t spine;
} GonkThugInput;

typedef enum {
    GONK_THUG_GROUND = 0,
    GONK_THUG_AIR,
    GONK_THUG_RAIL,
    GONK_THUG_WALLRIDE,
    GONK_THUG_WALLPLANT,
    GONK_THUG_LIP,
    GONK_THUG_UNKNOWN
} GonkThugState;

typedef struct {
    GonkVec3 position;
    GonkVec3 velocity;
    GonkVec3 up;
    GonkVec3 forward;
    GonkThugState state;
    int32_t rail_node;
    uint32_t terrain;
    uint8_t switched;
    uint8_t landed_this_frame;
} GonkThugPlayerState;

/*
 * World-query callbacks.
 *
 * The eventual goal is to let real THUG skating code ask GonkSkate's normalized
 * world the same kinds of questions it currently asks CFeeler/CCollCache.
 */
typedef struct {
    void* user;

    uint8_t (*raycast)(
        void* user,
        GonkVec3 start,
        GonkVec3 end,
        GonkVec3* hit_point,
        GonkVec3* hit_normal,
        uint32_t* terrain,
        uint32_t* flags
    );

    /*
     * Find a grind rail close enough to a query segment.
     * Returns 1 when a suitable rail is found.
     */
    uint8_t (*find_rail)(
        void* user,
        GonkVec3 start,
        GonkVec3 end,
        int32_t* rail_id,
        GonkVec3* nearest_point,
        GonkVec3* tangent
    );
} GonkThugWorldApi;

GonkThugHandle* gonk_thug_create(const GonkThugWorldApi* world);
void gonk_thug_destroy(GonkThugHandle* handle);

void gonk_thug_reset(
    GonkThugHandle* handle,
    GonkVec3 position,
    GonkVec3 forward
);

void gonk_thug_set_input(
    GonkThugHandle* handle,
    const GonkThugInput* input
);

void gonk_thug_step(
    GonkThugHandle* handle,
    float dt_seconds
);

void gonk_thug_get_state(
    const GonkThugHandle* handle,
    GonkThugPlayerState* out_state
);

#ifdef __cplusplus
}
#endif
