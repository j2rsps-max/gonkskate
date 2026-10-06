#include "session.h"
#include <sk/components/skatercorephysicscomponent.h>
#include <sk/components/skaterstatecomponent.h>
#include <sk/components/skaterflipandrotatecomponent.h>
#include <sk/components/skaterrotatecomponent.h>
#include <sk/components/skaterscorecomponent.h>
#include <sk/components/skaterbalancetrickcomponent.h>
#include <gel/components/inputcomponent.h>
#include <gel/components/trickcomponent.h>
#include <gel/components/triggercomponent.h>
#include <gel/components/movablecontactcomponent.h>
#include <gel/components/walkcomponent.h>
#include <gel/scripting/struct.h>
#include <sk/engine/feeler.h>
#include <gonkskate_thug_collision.h>
#include <map>
#include <string>

namespace Headless {
void enable_rails();GonkVec3 spawn();GonkVec3 facing();
extern uint64 collisions,lookups;
extern std::map<std::string,uint64> peripheral;
namespace {
uint64 calls(){uint64 result=0;for(const auto& entry:peripheral)result+=entry.second;return result;}
GonkVec3 vector(const Mth::Vector& v){return {v[X],v[Y],v[Z]};}
}
struct Session::Impl {
    std::unique_ptr<Obj::CSkater> skater=std::make_unique<Obj::CSkater>();
    Obj::CSkaterPhysicsControlComponent* control=nullptr;
    Obj::CSkaterCorePhysicsComponent* core=nullptr;
    Obj::CSkaterRotateComponent* rotate=nullptr;
    Script::CStruct params;
    ~Impl(){CFeeler::sClearDefaultCache();skater.reset();}
    void set_spawn(){
        auto p=spawn(),f=facing();skater->m_pos.Set(p.x,p.y,p.z);skater->m_old_pos=skater->m_pos;
        skater->m_matrix.Ident();skater->m_matrix[Z].Set(f.x,0,f.z,0);skater->m_matrix[X].Set(f.z,0,-f.x,0);
        skater->SetDisplayMatrix(skater->m_matrix);
    }
};
Session::Session(bool rails,bool ramp):impl_(std::make_unique<Impl>()) {
    auto& p=*impl_;auto* skater=p.skater.get();
    skater->AddComponent(new Obj::CSkaterStateComponent);
    skater->AddComponent(new Obj::CInputComponent);
    skater->AddComponent(new Obj::CSkaterScoreComponent);
    skater->AddComponent(new Obj::CTrickComponent);
    p.control=new Obj::CSkaterPhysicsControlComponent;skater->AddComponent(p.control);
    p.core=new Obj::CSkaterCorePhysicsComponent;skater->AddComponent(p.core);
    p.rotate=new Obj::CSkaterRotateComponent;skater->AddComponent(p.rotate);
    skater->AddComponent(new Obj::CTriggerComponent);
    skater->AddComponent(new Obj::CWalkComponent);
    skater->AddComponent(new Obj::CSkaterBalanceTrickComponent);
    skater->AddComponent(new Obj::CMovableContactComponent);
    skater->AddComponent(new Obj::CSkaterSoundComponent);
    skater->AddComponent(new Obj::CSkaterFlipAndRotateComponent);
    if(rails)enable_rails();
    for(Obj::CBaseComponent* c=GetSkaterStateComponentFromObject(skater);c;c=c->GetNext())c->InitFromStructure(&p.params);
    p.core->Finalize();p.rotate->Finalize();p.set_spawn();p.core->Reset();
    if(ramp){skater->m_pos[X]=-480;skater->m_old_pos=skater->m_pos;}
}
Session::~Session()=default;
Snapshot Session::state() const {
    const auto& p=*impl_;const auto* skater=p.skater.get();
    return {vector(skater->m_pos),vector(skater->m_vel),vector(skater->m_matrix[Z]),vector(skater->m_matrix[Y]),
            static_cast<int32_t>(p.core->GetState()),p.core->GetTerrain(),p.core->GetRailNode(),p.core->HaveLandedThisFrame()};
}
Snapshot Session::tick(const Controls& input){
    auto& p=*impl_;auto& pad=GetInputComponentFromObject(p.skater.get())->GetControlPad();
    if(input.reset){pad.Zero();p.core->InitFromStructure(&p.params);p.set_spawn();p.core->Reset();p.skater->m_old_pos=p.skater->m_pos;}
    pad.m_square.Update(input.push);pad.m_x.Update(input.crouch);
    pad.m_left.Update(input.left);pad.m_right.Update(input.right);
    pad.m_triangle.Update(input.grind);pad.m_down.Update(input.brake);
    auto queries=collisions,parameters=lookups,dependencies=calls();
    p.control->Update();p.core->Update();p.rotate->Update();
    // Original SkaterAdjustPhysics stores this after core/rotate. The profile
    // excludes its rendered/moving-object adjustments, as before extraction.
    p.skater->m_old_pos=p.skater->m_pos;
    auto result=state();result.queries=collisions-queries;result.lookups=lookups-parameters;
    result.adapter_calls=calls()-dependencies;return result;
}
void Session::probe_peripheral(){Obj::CManual manual;manual.DoManualPhysics();}
#ifdef GONK_THUG_RUNTIME_TESTING
void Session::probe_tick_collision_failure(){
    extern GonkThugCollisionApi world;
    struct Restore {GonkThugCollisionApi& world;uint32_t abi;~Restore(){world.abi_version=abi;}} restore{world,world.abi_version};
    // Force the real core's next feeler query to detect an unsupported ABI.
    // Original Update begins normally, including its default-cache setup.
    world.abi_version=0;tick({});
}
#endif
}
