#include "session.h"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <string>
#include <map>
#include <vector>
#include <gonkskate_thug.h>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif
namespace Headless {void load_world(const std::string&);extern uint64_t frame;extern std::map<std::string,uint64_t> peripheral;}
struct Input {int push=0,crouch=0,left=0,right=0,brake=0,grind=0,reset=0;};
static int run_cli(int argc,char** argv) {
    bool probe=false,pipe=false;std::string scenario="ollie",world_path;int modes=0;
    for(int i=1;i<argc;++i){
     std::string arg=argv[i];
     if(arg=="--pipe"){pipe=true;++modes;}
     else if(arg=="--probe-peripheral"){probe=true;++modes;}
     else if(arg=="--scenario" && i+1<argc){scenario=argv[++i];++modes;}
     else if(arg=="--world" && i+1<argc && world_path.empty())world_path=argv[++i];
     else{std::cerr<<"Invalid argument: "<<arg<<'\n';return 2;}
    }
    if(modes>1 || (scenario!="ollie" && scenario!="idle" && scenario!="steer" && scenario!="soak" && scenario!="rail" && scenario!="rail_jump" && scenario!="ramp")) {
        std::cerr<<"Usage: gonkskate-thug-test [--pipe | --scenario idle|ollie|steer|soak|rail|rail_jump|ramp] [--world file.gonkworld]\n";return 2;
    }
    if(!world_path.empty())try{Headless::load_world(world_path);}catch(const std::exception& error){std::cerr<<"WORLD_ERROR "<<error.what()<<'\n';return 2;}
    Headless::Session session(pipe || !world_path.empty() || scenario=="rail" || scenario=="rail_jump" || scenario=="ramp",scenario=="ramp");
    if(probe){session.probe_peripheral();return 1;}
    std::cout<<std::setprecision(9)<<"frame,push,crouch,left,right,brake,x,y,z,vx,vy,vz,fx,fy,fz,state,terrain,rail,landed,queries,lookups,adapter_calls,grind,reset,ux,uy,uz\n"<<std::flush;
    for(Headless::frame=0;pipe || Headless::frame<(scenario=="soak" ? 10000:360);++Headless::frame) {
        Input input;
        if(pipe) {
            std::string line;if(!std::getline(std::cin,line)) break;
            std::istringstream row(line);std::vector<int> values;std::string value;
            bool valid=true;
            while(row>>value) {
                if(value!="0" && value!="1") {valid=false;break;}
                values.push_back(value=="1");
            }
            valid=valid && values.size()>=5 && values.size()<=7;
            if(!valid) {std::cerr<<"Invalid input frame "<<Headless::frame<<'\n';return 2;}
            input={values[0],values[1],values[2],values[3],values[4],values.size()>5 ? values[5]:0,values.size()>6 ? values[6]:0};
        } else if(scenario!="idle") {
            input.push=Headless::frame>=30;
            input.crouch=Headless::frame>=150 && Headless::frame<165;
            if(scenario=="rail" || scenario=="rail_jump") input.grind=Headless::frame>=165;
            if(scenario=="rail_jump" && Headless::frame>=200 && Headless::frame<210) input.crouch=1;
            if(scenario=="ramp") input.crouch=0;
            if(scenario=="steer") {input.left=Headless::frame>=60 && Headless::frame<120;input.right=Headless::frame>=240 && Headless::frame<270;input.brake=Headless::frame>=300;input.push=Headless::frame>=30 && Headless::frame<300;}
            if(scenario=="soak") {input.crouch=Headless::frame%180>=120 && Headless::frame%180<150;input.left=Headless::frame%600>=200 && Headless::frame%600<300;}
        }
        Headless::Controls controls{uint8_t(input.push*255),uint8_t(input.crouch*255),uint8_t(input.left*255),uint8_t(input.right*255),uint8_t(input.brake*255),uint8_t(input.grind*255),uint8_t(input.reset)};
        const auto state=session.tick(controls);
        std::cout<<Headless::frame<<','<<input.push<<','<<input.crouch<<','<<input.left<<','<<input.right<<','<<input.brake<<','
                 <<state.position.x<<','<<state.position.y<<','<<state.position.z<<','
                 <<state.velocity.x<<','<<state.velocity.y<<','<<state.velocity.z<<','
                 <<state.forward.x<<','<<state.forward.y<<','<<state.forward.z<<','
                 <<state.state<<','<<state.terrain<<','<<state.rail<<','<<state.landed<<','
                 <<state.queries<<','<<state.lookups<<','<<state.adapter_calls<<','<<input.grind<<','<<input.reset<<','
                 <<state.up.x<<','<<state.up.y<<','<<state.up.z<<'\n'<<std::flush;
    }
    for(auto& p:Headless::peripheral) std::cerr<<"ADAPTER_CALL "<<p.first<<' '<<p.second<<'\n';
    return 0;
}
#ifdef _WIN32
int wmain(int argc,wchar_t** wide){
    // Windows provides UTF-16 arguments. The shared world reader/API uses UTF-8.
    std::vector<std::string> storage(argc);std::vector<char*> args(argc+1,nullptr);
    for(int index=0;index<argc;++index){
        const int bytes=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,wide[index],-1,nullptr,0,nullptr,nullptr);
        if(!bytes){std::cerr<<"Invalid Unicode command argument\n";return 2;}
        storage[index].resize(bytes);
        if(!WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,wide[index],-1,storage[index].data(),bytes,nullptr,nullptr))return 2;
        storage[index].pop_back();args[index]=storage[index].data();
    }
    return run_cli(argc,args.data());
}
#else
int main(int argc,char** argv){return run_cli(argc,argv);}
#endif
