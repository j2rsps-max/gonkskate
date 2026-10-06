#include <gonkskate_thug_runtime.h>
#include "session.h"
#include "embedded_fault.h"
#include <mutex>
#include <thread>
#include <cstdio>
#include <string>
#include <limits>

namespace Headless {extern uint64_t frame;void load_world(const std::string&);}
namespace {
struct Runtime {
    std::unique_ptr<Headless::Session> session;
    std::thread::id thread=std::this_thread::get_id();
    GonkThugRuntimeHandle id=0;
    uint64_t ticks=0;
    Headless::Snapshot last{};
    bool failed=false;
};
std::mutex gate;
std::unique_ptr<Runtime> active;
uint64_t next_id=1;
thread_local GonkThugRuntimeError last_error{};
int error(int code,const char* message,uint64_t frame=0){
    last_error={};last_error.status=code;last_error.frame=frame;
    std::snprintf(last_error.message,sizeof(last_error.message),"%s",message);return code;
}
int check(GonkThugRuntimeHandle id){
    if(!active || !id || active->id!=id)return error(GONK_RUNTIME_INVALID_HANDLE,"Invalid or expired runtime handle");
    if(active->thread!=std::this_thread::get_id())return error(GONK_RUNTIME_WRONG_THREAD,"Use the runtime on its creator thread");
    return GONK_RUNTIME_OK;
}
void state(GonkThugRuntimeState* out){
    *out={};out->abi_version=GONK_THUG_RUNTIME_ABI;out->struct_size=sizeof(*out);out->completed_ticks=active->ticks;
    const auto& p=active->last;out->position=p.position;out->velocity=p.velocity;out->forward=p.forward;out->up=p.up;
    out->native_state=p.state;out->terrain=p.terrain;out->rail_node=p.rail;out->landed_this_frame=p.landed;
    out->collision_queries=p.queries;out->parameter_lookups=p.lookups;out->adapter_calls=p.adapter_calls;
}
template<class F> int execute(GonkThugRuntimeHandle handle,F action){
    std::unique_lock lock(gate,std::try_to_lock);
    if(!lock.owns_lock())return error(GONK_RUNTIME_BUSY,"Runtime call already in progress");
    const int status=check(handle);if(status)return status;
    if(active->failed)return error(GONK_RUNTIME_FAILED,"Runtime failed; destroy and recreate before stepping",active->ticks);
    try {action();last_error={};return GONK_RUNTIME_OK;}
    catch(const Headless::Fault& fault){active->failed=true;return error(fault.code,fault.what(),Headless::frame);}
    catch(const std::exception& fault){active->failed=true;return error(GONK_RUNTIME_ERROR,fault.what(),Headless::frame);}
    catch(...){active->failed=true;return error(GONK_RUNTIME_ERROR,"Unknown runtime failure",Headless::frame);}
}
}
extern "C" {
uint32_t gonk_thug_runtime_abi_version(){return GONK_THUG_RUNTIME_ABI;}
int gonk_thug_runtime_create(const GonkThugRuntimeConfig* config,GonkThugRuntimeHandle* out){
    if(!config || !out)return error(GONK_RUNTIME_INVALID_ARGUMENT,"Missing configuration/output");
    *out=0;
    if(config->abi_version!=GONK_THUG_RUNTIME_ABI || config->struct_size<sizeof(*config))
        return error(GONK_RUNTIME_ABI_MISMATCH,"Runtime ABI/version or configuration size differs");
    if(config->flags&~GONK_RUNTIME_TEST_AREA || config->reserved ||
       (config->flags && config->world_path && *config->world_path))
        return error(GONK_RUNTIME_INVALID_ARGUMENT,"Invalid world/profile flags");
    std::unique_lock lock(gate,std::try_to_lock);
    if(!lock.owns_lock() || active)return error(GONK_RUNTIME_BUSY,"Only one live THUG runtime is supported");
    if(next_id==std::numeric_limits<uint64_t>::max())return error(GONK_RUNTIME_ERROR,"Runtime handle sequence exhausted");
    try {
        Headless::clear_environment();
        const bool imported=config->world_path && *config->world_path;
        if(imported)Headless::load_world(config->world_path);
        auto runtime=std::make_unique<Runtime>();
        runtime->session=std::make_unique<Headless::Session>(imported || config->flags);
        runtime->last=runtime->session->state();runtime->id=next_id++;
        *out=runtime->id;active=std::move(runtime);last_error={};return GONK_RUNTIME_OK;
    } catch(const Headless::Fault& fault){return error(fault.code,fault.what(),Headless::frame);}
      catch(const std::exception& fault){return error(GONK_RUNTIME_ERROR,fault.what(),Headless::frame);}
      catch(...){return error(GONK_RUNTIME_ERROR,"Unknown runtime creation failure");}
}
int gonk_thug_runtime_destroy(GonkThugRuntimeHandle handle){
    std::unique_lock lock(gate,std::try_to_lock);
    if(!lock.owns_lock())return error(GONK_RUNTIME_BUSY,"Runtime call already in progress");
    const int status=check(handle);if(status)return status;
    try {active.reset();Headless::clear_environment();last_error={};return GONK_RUNTIME_OK;}
    catch(const std::exception& fault){return error(GONK_RUNTIME_ERROR,fault.what());}
    catch(...){return error(GONK_RUNTIME_ERROR,"Unknown runtime destruction failure");}
}
int gonk_thug_runtime_step(GonkThugRuntimeHandle handle,const GonkThugRuntimeControls* input,GonkThugRuntimeState* out,uint32_t size){
    if(!input || !out || size<sizeof(*out) || input->reset>1 || input->reserved)
        return error(GONK_RUNTIME_INVALID_ARGUMENT,"Invalid controls/state buffer");
    return execute(handle,[&]{
        Headless::frame=active->ticks;
        active->last=active->session->tick({input->push,input->crouch,input->left,input->right,input->brake,input->grind,input->reset});
        ++active->ticks;state(out);
    });
}
int gonk_thug_runtime_get_state(GonkThugRuntimeHandle handle,GonkThugRuntimeState* out,uint32_t size){
    if(!out || size<sizeof(*out))return error(GONK_RUNTIME_INVALID_ARGUMENT,"Invalid state buffer");
    return execute(handle,[&]{state(out);});
}
int gonk_thug_runtime_get_error(GonkThugRuntimeError* out,uint32_t size){
    if(!out || size<sizeof(*out))return GONK_RUNTIME_INVALID_ARGUMENT;
    *out=last_error;return GONK_RUNTIME_OK;
}
#ifdef GONK_THUG_RUNTIME_TESTING
// Test-only export exercises a real unresolved THUG dependency through the
// generated trap and exception boundary; production libraries omit it.
GONK_THUG_RUNTIME_API int gonk_thug_runtime_test_fault(GonkThugRuntimeHandle handle){
    return execute(handle,[]{active->session->probe_peripheral();});
}
GONK_THUG_RUNTIME_API int gonk_thug_runtime_test_tick_fault(GonkThugRuntimeHandle handle){
    return execute(handle,[]{Headless::frame=active->ticks;active->session->probe_tick_collision_failure();});
}
#endif
}
