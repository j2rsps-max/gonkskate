#include <sk/components/skatercorephysicscomponent.h>
#include <sk/components/skaterrotatecomponent.h>
#include <sk/components/skaterscorecomponent.h>
#include <sk/components/skaterbalancetrickcomponent.h>
#include <sk/components/skaterstatecomponent.h>
#include <sk/objects/skatercareer.h>
#include <gel/components/inputcomponent.h>
#include <gel/components/triggercomponent.h>
#include <gel/components/trickcomponent.h>
#include <gel/components/movablecontactcomponent.h>
#include <gel/components/walkcomponent.h>
#include <gel/collision/collcache.h>
#include <gel/scripting/script.h>
#include <gel/scripting/struct.h>
#include <sk/modules/skate/skate.h>
#include <sk/gamenet/gamenet.h>
#include <sk/parkeditor2/parked.h>
#include <gonkskate_thug_params.h>
#include <gonkskate_thug_collision.h>
#include <map>
#include <string>
#include <cstdarg>
#include <iostream>

namespace Headless {
uint64 frame=0;
uint64 collisions=0, lookups=0;
GonkThugCollisionApi world={GONK_THUG_COLLISION_ABI_VERSION,nullptr,gonk_thug_flat_plane_query};
static_assert(mFD_SKATABLE==GONK_THUG_FACE_SKATABLE);
static_assert(vTERRAIN_CONCSMOOTH==GONK_THUG_TERRAIN_CONCRETE_SMOOTH);
std::map<std::string, uint64> peripheral;
void called(const char* name) { ++peripheral[name]; }
[[noreturn]] void unsupported(const char* name) {
    fprintf(stderr,"UNSUPPORTED frame=%llu %s\n",static_cast<unsigned long long>(frame),name);
    // Preserve the event/dependency identity even when a trap exits mid-update.
    for(const auto& call:peripheral) fprintf(stderr,"ADAPTER_CALL %s %llu\n",call.first.c_str(),static_cast<unsigned long long>(call.second));
    std::exit(3);
}
uint32 checksum(const char* text) {
    uint32 crc=0xffffffff;
    for (;*text;++text) {
        unsigned char c=*text;
        if(c>='A' && c<='Z') c+=32;
        crc ^= c;
        for(int b=0;b<8;++b) crc=(crc>>1) ^ ((crc&1) ? 0xedb88320 : 0);
    }
    return crc;
}
struct Scalar { uint32 checksum; const char* name; float value; };
#include "physics_scalars.inc"
float parameter(uint32 checksum) {
    ++lookups;
    for (const auto& p : scalars) if (p.checksum == checksum) return p.value;
    std::cerr << "missing parameter 0x" << std::hex << checksum << std::dec << '\n';
    unsupported("parameter");
}
}
extern "C" void gonk_unexpected_symbol(const char* name) { Headless::unsupported(name); }
int OurPrintf(const char* format, ...) { va_list args;va_start(args,format);int n=vfprintf(stderr,format,args);va_end(args);return n; }
uint32 check_checksum(uint32 crc, const char* text, const char*, int) {
    if (crc!=Headless::checksum(text)) Headless::unsupported("checksum verification");
    return crc;
}
namespace Mem { extern "C" { Manager* sp_instance=nullptr; } }
namespace Dbg {
char null_pointer_message[]="Null Pointer";
char* msg_null_pointer=null_pointer_message;
char sprintf_storage[8192];
char* sprintf_pad=sprintf_storage;
void pad_printf(const char* format, ...) { va_list args;va_start(args,format);vsnprintf(sprintf_pad,sizeof(sprintf_storage),format,args);va_end(args); }
void Assert(char* file, unsigned int line, char* message) {
    std::cerr << "THUG ASSERT " << file << ':' << line << " " << (message?message:"") << '\n';std::exit(4);
}
}
namespace Spt { void* Class::operator new(size_t size) { auto p=calloc(1,size); if(!p) throw std::bad_alloc();return p; } }
namespace Tmr {
Time GetTime() { return static_cast<Time>(Headless::frame*1000/60); }
float FrameLength() { return 1.0f/60.0f; }
uint64 GetRenderFrame() { return Headless::frame; }
}
bool g_CheatsEnabled=false;
namespace Obj {
bool DebugSkaterScripts=false;
CPendingTricks::CPendingTricks() {m_NumTrickItems=0;}
void CTrickComponent::SetGraffitiTrickStarted(bool started){Headless::called("SetGraffitiTrickStarted");m_graffiti_trick_started=started;}
void CTrickComponent::TrickOffObject(uint32 node){Headless::called("TrickOffObject");if(node) Headless::unsupported("trick object");}
CObject::CObject():m_node(this) {m_id=1;m_type=1;mp_tags=nullptr;mp_script=nullptr;mp_manager=nullptr;m_object_flags=0;m_ref_count=0;m_stamp=0;}
CObject::~CObject() {delete mp_script;}
void CObject::SetProperties(Script::CStruct*) { Headless::unsupported("object properties"); }
bool CObject::CallMemberFunction(uint32,Script::CStruct*,Script::CScript*) { Headless::unsupported("object script command"); }
void CObject::GetDebugInfo(Script::CStruct*) {}
bool CObject::PassTargetedEvent(CEvent*,bool) { Headless::unsupported("targeted event"); }
void CObject::SelfEvent(uint32 event,Script::CStruct*) {
    Headless::called(("SelfEvent:"+std::to_string(event)).c_str());
    // Flat-floor profile replaces the Ollied script handler with its public
    // Jump command. The core computes tense time before emitting this event.
    // Core already sets AIR before GroundGone, and bounce_off_wall computes
    // velocity/orientation around FlailLeft/Right. Their tricks.q handlers select
    // animation/rumble/trick queues and stop balance, absent in this profile.
    // Record the missing presentation explicitly; retain the original physics.
    if(event==0x3b1001b6) {Headless::called("GroundGone:no-animation-or-script-trick-queues");return;}
    if(event==0xb4101d70 || event==0x756a7535) {Headless::called(event==0xb4101d70 ? "FlailLeft:no-animation-or-rumble":"FlailRight:no-animation-or-rumble");return;}
    // Ground_Wallpush's Init_Wallpush is notification/rumble; the original core
    // reflects/damps velocity after this event. Model flip/score are unrendered.
    if(event==0x4c03635b) {Headless::called("WallPush:no-animation-or-script-score");return;}
    if(event!=0x8ffefb28 && event!=0x532b16ef && event!=0xafaa46ba) {
        char message[96];snprintf(message,sizeof(message),"unexpected skater self-event crc=0x%08x",event);
        Headless::unsupported(message);
    }
    if(event==0x8ffefb28) {
        Script::CStruct params;
        GetSkaterCorePhysicsComponentFromObject(static_cast<CCompositeObject*>(this))->CallMemberFunction(0x584cf9e9,&params,nullptr);
    }
}
void CObject::BroadcastEvent(uint32 event,Script::CStruct*,float) {Headless::called(("BroadcastEvent:"+std::to_string(event)).c_str());}
void CObject::RemoveEventHandler(uint32) {Headless::called("RemoveEventHandler");}
CCompositeObject::CCompositeObject() {m_vel.Set();m_pos.Set();m_old_pos.Set();m_matrix.Ident();m_display_matrix.Ident();mp_component_list=nullptr;m_composite_object_flags.ClearAll();}
CCompositeObject::~CCompositeObject() {while(mp_component_list) {auto next=mp_component_list->GetNext();delete mp_component_list;mp_component_list=next;}}
void CCompositeObject::AddComponent(CBaseComponent* component) {
    if(GetComponent(component->GetType())) Headless::unsupported("duplicate component");
    component->mp_next=nullptr;component->SetObj(this);
    if(!mp_component_list) mp_component_list=component;
    else {auto last=mp_component_list;while(last->mp_next) last=last->mp_next;last->mp_next=component;}
}
CBaseComponent* CCompositeObject::GetComponent(uint32 type) const {for(auto p=mp_component_list;p;p=p->GetNext()) if(p->GetType()==type) return p;return nullptr;}
bool CCompositeObject::CallMemberFunction(uint32,Script::CStruct*,Script::CScript*) {Headless::unsupported("composite script command");}
void CCompositeObject::GetDebugInfo(Script::CStruct*) {}
void CCompositeObject::SetTeleported(bool) {Headless::called("SetTeleported");m_composite_object_flags.Set(CO_TELEPORTED);}
void CCompositeObject::Update() {Headless::unsupported("nested composite update");}
CSkater::CSkater() {}
float CSkater::GetScriptedStat(uint32 id) {
    GonkThugStatContext context;gonk_thug_default_stat_context(&context);
    context.switched=GetSkaterCorePhysicsComponent()->IsSwitched();
    float value;
    for (const char* name : Headless::stat_names) if(Headless::checksum(name)==id) {
        if(gonk_thug_get_scripted_stat(name,&context,&value)) {++Headless::lookups;return value;}
    }
    Headless::unsupported("scripted stat");
}
float GetPhysicsFloat(uint32 id, Script::EAssertType) {return Headless::parameter(id);}
int GetPhysicsInt(uint32 id, Script::EAssertType) {return static_cast<int>(Headless::parameter(id));}
#define PEER(CLASS, CRC) \
CLASS::CLASS() {SetType(CRC);} \
CLASS::~CLASS() {} \
void CLASS::Update() {Headless::called(#CLASS "::Update");} \
void CLASS::InitFromStructure(Script::CStruct*) {} \
CBaseComponent::EMemberFunctionResult CLASS::CallMemberFunction(uint32,Script::CStruct*,Script::CScript*) {Headless::unsupported(#CLASS "::CallMemberFunction");} \
void CLASS::GetDebugInfo(Script::CStruct*) {}
void CInputComponent::RefreshFromStructure(Script::CStruct* p) {InitFromStructure(p);}
PEER(CInputComponent, CRC_INPUT)
void CSkaterSoundComponent::RefreshFromStructure(Script::CStruct* p) {InitFromStructure(p);}
PEER(CSkaterSoundComponent, CRC_SKATERSOUND)
void CTriggerComponent::RefreshFromStructure(Script::CStruct* p) {InitFromStructure(p);}
PEER(CTriggerComponent, CRC_TRIGGER)
PEER(CTrickComponent, CRC_TRICK)
void CSkaterBalanceTrickComponent::RefreshFromStructure(Script::CStruct* p) {InitFromStructure(p);}
PEER(CSkaterBalanceTrickComponent, CRC_SKATERBALANCETRICK)
void CMovableContactComponent::RefreshFromStructure(Script::CStruct* p) {InitFromStructure(p);}
PEER(CMovableContactComponent, CRC_MOVABLECONTACT)
void CWalkComponent::RefreshFromStructure(Script::CStruct* p) {InitFromStructure(p);}
PEER(CWalkComponent, CRC_WALK)
CSkaterScoreComponent::CSkaterScoreComponent() {SetType(CRC_SKATERSCORE);mp_score=new Mdl::Score;}
CSkaterScoreComponent::~CSkaterScoreComponent() {delete mp_score;}
void CSkaterScoreComponent::Update() {}
void CSkaterScoreComponent::InitFromStructure(Script::CStruct*) {}
void CSkaterScoreComponent::RefreshFromStructure(Script::CStruct*) {}
CBaseComponent::EMemberFunctionResult CSkaterScoreComponent::CallMemberFunction(uint32,Script::CStruct*,Script::CScript*) {Headless::unsupported("score command");}
void CSkaterScoreComponent::GetDebugInfo(Script::CStruct*) {}
CSkaterPhysicsControlComponent::CSkaterPhysicsControlComponent() {SetType(CRC_SKATERPHYSICSCONTROL);m_restarted_this_frame=false;m_physics_suspended=false;}
CSkaterPhysicsControlComponent::~CSkaterPhysicsControlComponent() {}
void CSkaterPhysicsControlComponent::InitFromStructure(Script::CStruct*) {mp_state_component=GetSkaterStateComponentFromObject(GetObject());mp_state_component->m_physics_state=SKATING;mp_state_component->m_driving=false;}
void CSkaterPhysicsControlComponent::RefreshFromStructure(Script::CStruct* p) {InitFromStructure(p);}
void CSkaterPhysicsControlComponent::Finalize() {}
void CSkaterPhysicsControlComponent::Update() {m_restarted_this_frame=false;}
CBaseComponent::EMemberFunctionResult CSkaterPhysicsControlComponent::CallMemberFunction(uint32,Script::CStruct*,Script::CScript*) {Headless::unsupported("physics control command");}
void CSkaterPhysicsControlComponent::GetDebugInfo(Script::CStruct*) {}
CManual::CManual() {}
CManual::~CManual() {}
void CSkaterSoundComponent::PlayLandSound(float,ETerrainType) {Headless::called("PlayLandSound");}
void CSkaterSoundComponent::PlayJumpSound(float,ETerrainType) {Headless::called("PlayJumpSound");}
void CSkaterSoundComponent::PlayBonkSound(float,ETerrainType) {Headless::called("PlayBonkSound:no-audio");}
void CTriggerComponent::CheckFeelerForTrigger(int,CFeeler& feeler) {Headless::called("CheckFeelerForTrigger");if(feeler.GetTrigger()) Headless::unsupported("world trigger");}
bool CMovableContactComponent::CheckForMovableContact(CFeeler& feeler) {Headless::called("CheckForMovableContact");if(feeler.IsMovableCollision()) Headless::unsupported("moving collision");return false;}
CSkaterCareer::CSkaterCareer() {}
CSkaterCareer::~CSkaterCareer() {}
bool CSkaterCareer::GetCheat(uint32) {Headless::called("GetCheat");return false;}
}
namespace Mdl {
Score::Score():m_historyTab(16),m_infoTab(8) {}
Score::~Score() {}
void Score::TweakTrick(int){Headless::called("Score::TweakTrick:no-scoring");}
void Score::UpdateSpin(int) {Headless::called("Score::UpdateSpin");}
void Score::UpdateRobotDetection(int) {Headless::called("Score::UpdateRobotDetection");}
Skate* Skate::Instance() {static Skate s{};return &s;}
Obj::CSkaterCareer* Skate::GetCareer() {static Obj::CSkaterCareer c;return &c;}
}
namespace Ed {CParkEditor* CParkEditor::Instance() {static CParkEditor p;return &p;} bool CParkEditor::UsingCustomPark(){Headless::called("UsingCustomPark");return false;}}
namespace GameNet {Manager* Manager::Instance(){static Manager m;return &m;}bool Manager::InNetGame(){Headless::called("InNetGame");return false;}}
namespace Nx {
CCollCache::CCollCache():m_array_size(0),m_num_static_coll(0),m_num_movable_coll(0) {}
CCollCache::~CCollCache() {}
void CCollCache::Update(const Mth::CBBox&) {Headless::called("CollisionCache::Update");}
CCollCache* CCollCacheManager::sCreateCollCache() {return new CCollCache;}
void CCollCacheManager::sDestroyCollCache(CCollCache* c) {delete c;}
}
Nx::CCollCache* CFeeler::sp_default_cache=nullptr;
void CFeeler::init(){memset(&m_col_data,0,sizeof(m_col_data));m_col_data.terrain=vTERRAIN_CONCSMOOTH;m_dist=0;m_point.Set();m_normal.Set(0,1,0);mp_callback=nullptr;mp_callback_data=nullptr;mp_cache=nullptr;m_movable_collision_id=0;}
CFeeler::CFeeler(){init();}
CFeeler::CFeeler(const Mth::Vector& start,const Mth::Vector& end){init();SetLine(start,end);}
void CFeeler::SetLine(const Mth::Vector& start,const Mth::Vector& end){m_start=start;m_end=end;}
void CFeeler::SetIgnore(uint16 ignore1,uint16 ignore0){m_col_data.ignore_1=ignore1;m_col_data.ignore_0=ignore0;}
bool CFeeler::GetCollision(bool,bool far) {
    ++Headless::collisions;
    if(Headless::world.abi_version!=GONK_THUG_COLLISION_ABI_VERSION || !Headless::world.query)
        Headless::unsupported("collision ABI");
    GonkThugCollisionQuery query={{m_start[X],m_start[Y],m_start[Z]},
        {m_end[X],m_end[Y],m_end[Z]},m_col_data.ignore_1,m_col_data.ignore_0,static_cast<uint8_t>(far)};
    GonkThugCollisionHit hit={};
    m_col_data.coll_found=false;
    if(!Headless::world.query(Headless::world.user,&query,&hit)) return false;
    if(hit.movable || hit.trigger || hit.node_name || hit.script)
        Headless::unsupported("flat-floor profile received moving/trigger/script world data");
    m_dist=hit.fraction;m_point.Set(hit.point.x,hit.point.y,hit.point.z);m_normal.Set(hit.normal.x,hit.normal.y,hit.normal.z);
    m_col_data.dist=m_dist;m_col_data.surface.point=m_point;m_col_data.surface.normal=m_normal;
    m_col_data.flags=hit.flags;m_col_data.terrain=static_cast<ETerrainType>(hit.terrain);
    m_col_data.coll_found=true;
    m_col_data.trigger=hit.trigger;m_col_data.script=hit.script;m_col_data.node_name=hit.node_name;m_col_data.p_coll_object=nullptr;
    if(mp_callback) mp_callback(this);
    return true;
}
bool CFeeler::IsMovableCollision(){return false;}
Obj::CCompositeObject* CFeeler::GetMovingObject(){return nullptr;}
namespace Script {
CStruct::CStruct(){mp_components=nullptr;}
CStruct::~CStruct(){}
bool CStruct::ContainsFlag(uint32) const{return false;}
bool CStruct::GetFloat(uint32,float*,EAssertType assert) const {if(assert==ASSERT) Headless::unsupported("required struct float");return false;}
bool CStruct::GetInteger(uint32,int*,EAssertType assert) const {if(assert==ASSERT) Headless::unsupported("required struct int");return false;}
int GetInteger(const char* name,EAssertType){return static_cast<int>(Headless::parameter(Headless::checksum(name)));}
int GetInteger(uint32 id,EAssertType){return static_cast<int>(Headless::parameter(id));}
float GetFloat(uint32 id,EAssertType){return Headless::parameter(id);}
int GetInt(uint32 id,bool){return static_cast<int>(Headless::parameter(id));}
const char* FindChecksumName(uint32){return "checksum";}
}
