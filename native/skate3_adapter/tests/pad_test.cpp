#include "gonkskate_skate3_pad.h"
#include <rex/input/input.h>
#include <array>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <string>
static void check(bool x,const char* message){if(!x){std::cerr<<message<<'\n';std::exit(1);}}
int main(int argc,char** argv){
 if(argc==2 && std::string(argv[1])=="--pipe"){
  std::string line;
  while(std::getline(std::cin,line)){
   GonkSkate3PadFrame f{};uint64_t packet,buttons;std::string extra;
   std::istringstream row(line);std::array<uint8_t,16> out;
   if(!(row>>packet>>buttons>>f.left_x>>f.left_y>>f.right_x>>f.right_y>>f.left_trigger>>f.right_trigger) || row>>extra || packet>UINT32_MAX || buttons>UINT32_MAX) return 2;
   f.packet_number=uint32_t(packet);f.godot_buttons=uint32_t(buttons);
   if(!gonk_skate3_encode_pad(&f,out.data())) return 2;
   for(auto b:out) std::cout<<std::hex<<std::setfill('0')<<std::setw(2)<<unsigned(b);
   std::cout<<'\n'<<std::flush;
  }
  return 0;
 }
 check(argc==1,"Usage: gonkskate-skate3-input-test [--pipe]");
 GonkSkate3PadFrame f={0x01020304,1,1,-1,-1,1,0.5f,1};std::array<uint8_t,16> out;
 check(gonk_skate3_encode_pad(&f,out.data()),"encode failed");
 const std::array<uint8_t,16> golden={1,2,3,4,0x10,0,128,255,0x7f,0xff,0x7f,0xff,0x80,0,0x80,0};
 check(out==golden,"SDK guest bytes/axis orientation mismatch");
 constexpr uint16_t masks[]={0x1000,0x2000,0x4000,0x8000,0x20,0x400,0x10,0x40,0x80,0x100,0x200,1,2,4,8};
 for(unsigned i=0;i<15;++i){f.godot_buttons=1u<<i;check(gonk_skate3_encode_pad(&f,out.data()),"button encode");rex::input::X_INPUT_STATE s;std::memcpy(&s,out.data(),16);check(uint16_t(s.gamepad.buttons)==masks[i],"button mapping");}
 f.godot_buttons=0;f.left_x=0.5f;f.right_x=-0.5f;f.left_trigger=-1;f.right_trigger=2;
 check(gonk_skate3_encode_pad(&f,out.data()),"range conversion");
 rex::input::X_INPUT_STATE s;std::memcpy(&s,out.data(),16);
 check(int16_t(s.gamepad.thumb_lx)==16384 && int16_t(s.gamepad.thumb_rx)==-16384,"half axes");
 check(s.gamepad.left_trigger==0 && s.gamepad.right_trigger==255,"trigger clamping");
 f.left_x=INFINITY;auto before=out;check(!gonk_skate3_encode_pad(&f,out.data()) && out==before,"invalid input must leave output untouched");
 check(!gonk_skate3_encode_pad(nullptr,out.data()),"null rejection");
 std::cout<<"SKATE3_INPUT_TEST passed: real SDK layout, byte order, 15 buttons, dual sticks, triggers, bounds\n";
}
