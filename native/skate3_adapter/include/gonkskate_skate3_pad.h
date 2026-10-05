#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Raw Godot axes: X right-positive, Y down-positive; no extra deadzone.
typedef struct GonkSkate3PadFrame {
 uint32_t packet_number, godot_buttons;
 float left_x,left_y,right_x,right_y,left_trigger,right_trigger;
} GonkSkate3PadFrame;
// Encodes the 16-byte, big-endian ReXGlue guest X_INPUT_STATE.
// Invalid/non-finite input leaves output untouched. Connection is separate.
uint8_t gonk_skate3_encode_pad(const GonkSkate3PadFrame* frame,uint8_t out_state[16]);
// Latest-state mailbox for a future ReXGlue driver. Polls never consume input.
// The host owns submission cadence; this API does not advance simulation time.
typedef struct GonkSkate3Input GonkSkate3Input;
GonkSkate3Input* gonk_skate3_input_create(void);
// Destroy only after every submitting/polling thread has stopped.
void gonk_skate3_input_destroy(GonkSkate3Input* input);
uint8_t gonk_skate3_input_submit(GonkSkate3Input* input,uint8_t connected,const GonkSkate3PadFrame* frame);
// Returns SDK X_RESULT. Only slot 0 is hosted; a null output is a status query.
// active=0 suppresses gamepad fields for guest UI gating, preserving raw state.
uint32_t gonk_skate3_input_poll(GonkSkate3Input* input,uint32_t user_index,uint8_t active,uint8_t out_state[16]);
// Latest rumble request from the guest, in host byte order. The host must send
// these speeds to its physical controller; reading never consumes a request.
typedef struct GonkSkate3Rumble {
 uint32_t sequence;
 uint16_t left_motor, right_motor;
} GonkSkate3Rumble;
uint32_t gonk_skate3_input_set_rumble(GonkSkate3Input* input,uint32_t user_index,uint16_t left_motor,uint16_t right_motor);
// Returns success even while disconnected, so the host can observe stop requests.
uint32_t gonk_skate3_input_get_rumble(GonkSkate3Input* input,GonkSkate3Rumble* out_rumble);
#ifdef __cplusplus
}
#endif
