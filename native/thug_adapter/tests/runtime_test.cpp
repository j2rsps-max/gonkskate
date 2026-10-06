#include <gonkskate_thug_runtime.h>
#include <iostream>
#include <iomanip>
#include <thread>
#include <vector>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <sstream>
#include <filesystem>
#include <fstream>
#ifdef GONK_THUG_RUNTIME_TESTING
extern "C" GONK_THUG_RUNTIME_API int gonk_thug_runtime_test_fault(GonkThugRuntimeHandle);
extern "C" GONK_THUG_RUNTIME_API int gonk_thug_runtime_test_tick_fault(GonkThugRuntimeHandle);
#endif
void Check(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
GonkThugRuntimeHandle Create(const char* world=nullptr,bool area=true){
    GonkThugRuntimeConfig config{1,sizeof(config),area && !world ? GONK_RUNTIME_TEST_AREA:0,0,world};
    GonkThugRuntimeHandle handle=0;Check(gonk_thug_runtime_create(&config,&handle)==0 && handle,"Create failed");return handle;
}
std::vector<GonkThugRuntimeState> Run(GonkThugRuntimeHandle handle){
    std::vector<GonkThugRuntimeState> states;
    for(int frame=0;frame<360;++frame){
        GonkThugRuntimeControls input{};input.push=frame>=30 ? 255:0;input.crouch=frame>=150 && frame<165 ? 255:0;
        GonkThugRuntimeState out{};Check(gonk_thug_runtime_step(handle,&input,&out,sizeof(out))==0,"Fixed tick failed");
        states.push_back(out);
    }
    return states;
}
void Contracts(){
    Check(gonk_thug_runtime_abi_version()==1,"ABI version");
    GonkThugRuntimeConfig bad{2,sizeof(bad),0,0,nullptr};GonkThugRuntimeHandle handle=99;
    Check(gonk_thug_runtime_create(&bad,&handle)==GONK_RUNTIME_ABI_MISMATCH && handle==0,"ABI mismatch");
    bad.abi_version=1;bad.world_path="missing-runtime-contract-world.gonkworld";
    Check(gonk_thug_runtime_create(&bad,&handle)==GONK_RUNTIME_ERROR && handle==0,"Invalid world failed open");
    handle=Create();GonkThugRuntimeHandle duplicate=0;
    bad.world_path=nullptr;
    Check(gonk_thug_runtime_create(&bad,&duplicate)==GONK_RUNTIME_BUSY && duplicate==0,"Duplicate runtime");
    GonkThugRuntimeState state{};GonkThugRuntimeControls input{};
    Check(gonk_thug_runtime_get_state(handle,&state,sizeof(state))==0 && state.completed_ticks==0,"Initial state");
    std::thread wrong([&]{
        GonkThugRuntimeState out{};
        Check(gonk_thug_runtime_step(handle,&input,&out,sizeof(out))==GONK_RUNTIME_WRONG_THREAD,"Wrong thread permitted");
        GonkThugRuntimeError error{};
        Check(gonk_thug_runtime_get_error(&error,sizeof(error))==0 && error.status==GONK_RUNTIME_WRONG_THREAD,"Thread-local error");
    });wrong.join();
    GonkThugRuntimeError error{};gonk_thug_runtime_get_error(&error,sizeof(error));
    Check(error.status==0,"Other thread changed creator error");
    Check(gonk_thug_runtime_step(handle,&input,&state,1)==GONK_RUNTIME_INVALID_ARGUMENT,"Short buffer accepted");
    input.reset=2;Check(gonk_thug_runtime_step(handle,&input,&state,sizeof(state))==GONK_RUNTIME_INVALID_ARGUMENT,"Invalid reset accepted");input.reset=0;
    auto first=Run(handle);
    Check(first[165].native_state==1 && first[203].landed_this_frame,"Authentic ollie/landing");
    for(const auto& p:first)Check(std::isfinite(p.position.y) && p.position.y>=0,"Invalid pose");
    Check(gonk_thug_runtime_destroy(handle)==0,"Destroy failed");
    auto fresh=Create();Check(fresh!=handle,"Stale handle reused");
    Check(gonk_thug_runtime_get_state(handle,&state,sizeof(state))==GONK_RUNTIME_INVALID_HANDLE,"Expired handle accepted");
    auto second=Run(fresh);
    for(size_t i=0;i<first.size();++i){
        const auto& a=first[i];const auto& b=second[i];
        Check(std::memcmp(&a.position,&b.position,sizeof(GonkVec3))==0 && std::memcmp(&a.velocity,&b.velocity,sizeof(GonkVec3))==0 &&
              std::memcmp(&a.forward,&b.forward,sizeof(GonkVec3))==0 && std::memcmp(&a.up,&b.up,sizeof(GonkVec3))==0 &&
              a.native_state==b.native_state && a.rail_node==b.rail_node && a.landed_this_frame==b.landed_this_frame &&
              a.collision_queries==b.collision_queries && a.parameter_lookups==b.parameter_lookups && a.adapter_calls==b.adapter_calls,
              "Destroy/recreate diverged");
    }
    input.reset=1;Check(gonk_thug_runtime_step(fresh,&input,&state,sizeof(state))==0,"Reset failed");
    Check(state.position.x==0 && state.position.y==0 && state.position.z==0 && state.native_state==0 && !state.landed_this_frame,"Reset pose/landing");
#ifdef GONK_THUG_RUNTIME_TESTING
    Check(gonk_thug_runtime_test_fault(fresh)==GONK_RUNTIME_UNSUPPORTED,"Unsupported dependency escaped boundary");
    Check(gonk_thug_runtime_get_error(&error,sizeof(error))==0 && std::strstr(error.message,"CManual::DoManualPhysics"),"Fault identity missing");
    input.reset=0;
    Check(gonk_thug_runtime_step(fresh,&input,&state,sizeof(state))==GONK_RUNTIME_FAILED,"Failed engine resumed");
#endif
    Check(gonk_thug_runtime_destroy(fresh)==0,"Failed runtime cleanup");
    fresh=Create(nullptr,false); // Ensure rail/import globals did not survive teardown.
    Check(gonk_thug_runtime_step(fresh,&input,&state,sizeof(state))==0 && state.completed_ticks==1,"Fresh runtime after failure");
    Check(gonk_thug_runtime_destroy(fresh)==0,"Final cleanup");
#ifdef GONK_THUG_RUNTIME_TESTING
    fresh=Create(nullptr,false);
    Check(gonk_thug_runtime_test_tick_fault(fresh)==GONK_RUNTIME_UNSUPPORTED,"Failure inside original Update escaped the host");
    Check(gonk_thug_runtime_get_error(&error,sizeof(error))==0 && error.frame==0 && std::strstr(error.message,"collision ABI"),"Tick failure identity missing");
    Check(gonk_thug_runtime_get_state(fresh,&state,sizeof(state))==GONK_RUNTIME_FAILED,"Partially updated state escaped");
    Check(gonk_thug_runtime_destroy(fresh)==0,"Tick failure teardown");
    fresh=Create();auto after_fault=Run(fresh);
    Check(std::memcmp(&after_fault[203].position,&first[203].position,sizeof(GonkVec3))==0 && after_fault[203].landed_this_frame,"Recreate after incomplete Update diverged");
    Check(gonk_thug_runtime_destroy(fresh)==0,"Tick recovery cleanup");
#endif
    const char* filename=u8"runtime-\u03c0.gonkworld";
    const auto path=std::filesystem::u8path(filename);
    Check(!std::filesystem::exists(path),"UTF-8 contract fixture already exists; preserve it and use a clean test directory");
    {
        std::ofstream file(path,std::ios::binary);file.write("GNKWLD1\0",8);
        const uint32_t header[]={1,0,0,1,0,0,0,0,0,0x3f800000};
        file.write(reinterpret_cast<const char*>(header),sizeof(header));
    }
    fresh=Create(filename);
    Check(gonk_thug_runtime_step(fresh,&input,&state,sizeof(state))==0,"UTF-8 imported world failed");
    Check(gonk_thug_runtime_destroy(fresh)==0,"Imported world cleanup");
    std::filesystem::remove(path);
    std::cout<<"Native runtime contracts passed: real fixed ticks, thread ownership, ABI, replay, reset, stale handles and fault containment\n";
}
void Trace(const char* world,bool area){
    auto handle=Create(world,area);
    std::cout<<std::setprecision(9)<<"frame,push,crouch,left,right,brake,x,y,z,vx,vy,vz,fx,fy,fz,state,terrain,rail,landed,queries,lookups,adapter_calls,grind,reset,ux,uy,uz\n";
    std::string line;
    while(std::getline(std::cin,line)){
        std::istringstream row(line);int push,crouch,left,right,brake,grind,reset;
        Check(bool(row>>push>>crouch>>left>>right>>brake>>grind>>reset),"Invalid trace input");
        for(auto flag:{push,crouch,left,right,brake,grind,reset})Check(flag==0 || flag==1,"Invalid control flag");
        GonkThugRuntimeControls input{uint8_t(push*255),uint8_t(crouch*255),uint8_t(left*255),uint8_t(right*255),uint8_t(brake*255),uint8_t(grind*255),uint8_t(reset),0};
        GonkThugRuntimeState p{};Check(gonk_thug_runtime_step(handle,&input,&p,sizeof(p))==0,"Trace step failed");
        std::cout<<p.completed_ticks-1<<','<<push<<','<<crouch<<','<<left<<','<<right<<','<<brake<<','
                 <<p.position.x<<','<<p.position.y<<','<<p.position.z<<','<<p.velocity.x<<','<<p.velocity.y<<','<<p.velocity.z<<','
                 <<p.forward.x<<','<<p.forward.y<<','<<p.forward.z<<','<<p.native_state<<','<<p.terrain<<','<<p.rail_node<<','
                 <<int(p.landed_this_frame)<<','<<p.collision_queries<<','<<p.parameter_lookups<<','<<p.adapter_calls<<','<<grind<<','<<reset<<','
                 <<p.up.x<<','<<p.up.y<<','<<p.up.z<<'\n';
    }
    Check(gonk_thug_runtime_destroy(handle)==0,"Trace cleanup");
}
int main(int argc,char** argv){
    try{if(argc>1 && std::string(argv[1])=="--trace"){
        const bool flat=argc>2 && std::string(argv[2])=="--flat";
        Trace(argc>2 && !flat ? argv[2]:nullptr,!flat);
    }else Contracts();return 0;}
    catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
