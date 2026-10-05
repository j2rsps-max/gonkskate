#include "gonkskate_skate3_pad.h"
#include <rex/input/input.h>
#include <rex/system/xtypes.h>
#include <array>
#include <cstring>
#include <mutex>
#include <new>
using namespace rex;
struct GonkSkate3Input {
 std::mutex mutex;
 std::array<uint8_t,16> state{};
 uint32_t packet=0;
 bool connected=false;
};
extern "C" GonkSkate3Input* gonk_skate3_input_create(){return new(std::nothrow) GonkSkate3Input;}
extern "C" void gonk_skate3_input_destroy(GonkSkate3Input* input){delete input;}
extern "C" uint8_t gonk_skate3_input_submit(GonkSkate3Input* input,uint8_t connected,const GonkSkate3PadFrame* frame){
 if(!input || connected>1) return 0;
 std::array<uint8_t,16> next{};
 if(connected && !gonk_skate3_encode_pad(frame,next.data())) return 0;
 std::lock_guard lock(input->mutex);
 if(input->connected!=bool(connected) || std::memcmp(input->state.data()+4,next.data()+4,12)!=0) ++input->packet;
 input->connected=connected;
 rex::be<uint32_t> packet=input->packet;
 std::memcpy(next.data(),&packet,4);
 input->state=next;
 return 1;
}
extern "C" uint32_t gonk_skate3_input_poll(GonkSkate3Input* input,uint32_t user_index,uint8_t active,uint8_t out[16]){
 if(!input || active>1) return X_ERROR_BAD_ARGUMENTS;
 std::lock_guard lock(input->mutex);
 if(user_index!=0 || !input->connected) return X_ERROR_DEVICE_NOT_CONNECTED;
 if(out){
  std::memcpy(out,input->state.data(),16);
  if(!active) std::memset(out+4,0,12);
 }
 return X_ERROR_SUCCESS;
}
