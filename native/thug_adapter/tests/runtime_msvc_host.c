/* No-CRT Windows host compiled with Clang's MSVC ABI. Compiler-provided stdint
 * suffices; this tests the real MinGW-built DLL/import library across ABIs. */
#include <gonkskate_thug_runtime.h>
__declspec(dllimport) void __stdcall ExitProcess(unsigned int);
int _fltused=0;
void mainCRTStartup(void){
    GonkThugRuntimeConfig config={GONK_THUG_RUNTIME_ABI,sizeof(config),0,0,0};
    GonkThugRuntimeHandle handle=0;
    GonkThugRuntimeState state;
    GonkThugRuntimeControls input={255,0,0,0,0,0,0,0};
    if(gonk_thug_runtime_abi_version()!=1 || gonk_thug_runtime_create(&config,&handle))ExitProcess(10);
    for(int i=0;i<60;++i)
        if(gonk_thug_runtime_step(handle,&input,&state,sizeof(state)))ExitProcess(11);
    if(state.completed_ticks!=60 || state.native_state!=0 || state.position.z<=0 || state.struct_size!=sizeof(state))ExitProcess(12);
    if(gonk_thug_runtime_destroy(handle))ExitProcess(13);
    ExitProcess(0);
}
