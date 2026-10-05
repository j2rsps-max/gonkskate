#include "gonkskate_skate3_pad.h"
#include <rex/input/input.h>
#include <algorithm>
#include <cmath>
#include <cstring>
static int16_t axis(float x){x=std::clamp(x,-1.0f,1.0f);return int16_t(std::lround(x*(x<0 ? 32768.0f:32767.0f)));}
static uint8_t trigger(float x){return uint8_t(std::lround(std::clamp(x,0.0f,1.0f)*255.0f));}
extern "C" uint8_t gonk_skate3_encode_pad(const GonkSkate3PadFrame* f,uint8_t out[16]){
 if(!f || !out) return 0;
 for(float v:{f->left_x,f->left_y,f->right_x,f->right_y,f->left_trigger,f->right_trigger}) if(!std::isfinite(v)) return 0;
 // Godot standard gamepad button IDs 0..14 map to the SDK enum, not THUG actions.
 using namespace rex::input;
 constexpr uint16_t buttons[]={X_INPUT_GAMEPAD_A,X_INPUT_GAMEPAD_B,X_INPUT_GAMEPAD_X,X_INPUT_GAMEPAD_Y,
  X_INPUT_GAMEPAD_BACK,X_INPUT_GAMEPAD_GUIDE,X_INPUT_GAMEPAD_START,X_INPUT_GAMEPAD_LEFT_THUMB,
  X_INPUT_GAMEPAD_RIGHT_THUMB,X_INPUT_GAMEPAD_LEFT_SHOULDER,X_INPUT_GAMEPAD_RIGHT_SHOULDER,
  X_INPUT_GAMEPAD_DPAD_UP,X_INPUT_GAMEPAD_DPAD_DOWN,X_INPUT_GAMEPAD_DPAD_LEFT,X_INPUT_GAMEPAD_DPAD_RIGHT};
 uint16_t mask=0;for(unsigned i=0;i<15;++i) if(f->godot_buttons&(1u<<i)) mask|=buttons[i];
 X_INPUT_STATE state{};static_assert(sizeof(state)==16);
 state.packet_number=f->packet_number;state.gamepad.buttons=mask;
 state.gamepad.left_trigger=trigger(f->left_trigger);state.gamepad.right_trigger=trigger(f->right_trigger);
 state.gamepad.thumb_lx=axis(f->left_x);state.gamepad.thumb_ly=axis(-f->left_y);
 state.gamepad.thumb_rx=axis(f->right_x);state.gamepad.thumb_ry=axis(-f->right_y);
 std::memcpy(out,&state,sizeof(state));return 1;
}
