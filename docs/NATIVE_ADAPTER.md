# Native adapter boundary

The current public foundations for THUG and Skate 3 are C/C++ oriented.

Rather than forcing a full rewrite immediately, GonkSkate should use a narrow C ABI between
the Rust host and native gameplay adapters.

Example future ABI:

```c
typedef struct {
    float move_x;
    float move_y;
    unsigned char jump_pressed;
    unsigned char crouch;
} GonkInput;

typedef struct {
    float position[3];
    float velocity[3];
    unsigned char grounded;
} GonkPlayerState;

typedef struct GonkPhysicsHandle GonkPhysicsHandle;

GonkPhysicsHandle* gonk_create_backend(void);
void gonk_destroy_backend(GonkPhysicsHandle*);
void gonk_on_map_loaded(GonkPhysicsHandle*, const char* normalized_map_path);
void gonk_step(
    GonkPhysicsHandle*,
    float dt,
    const GonkInput*,
    GonkPlayerState*
);
```

The first adapter should be THUG because its available source is easier to inspect and isolate.
Once that boundary works, the Skate 3 recomp can be studied for the smallest equivalent integration seam.
