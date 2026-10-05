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
#ifdef __cplusplus
}
#endif
