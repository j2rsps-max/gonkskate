#include <sk/objects/rail.h>
#include <gonkskate_thug_mesh.h>
#include <gonkskate_world.h>
#include "test_world.inc"
#include <sk/modules/skate/skate.h>
#include <sk/components/skaterflipandrotatecomponent.h>
#include <gel/components/trickcomponent.h>
#include <gel/scripting/array.h>
#include <gel/scripting/script.h>
#include <map>
#include <string>
namespace Headless {void called(const char*);[[noreturn]] void unsupported(const char*);uint32 checksum(const char*);bool rails_enabled=false;extern GonkThugCollisionApi world;}
namespace Headless {
Gonk::World imported_world;
bool imported=false;
GonkVec3 spawn(){return imported ? imported_world.spawn:GonkVec3{0,0,0};}
GonkVec3 facing(){return imported ? imported_world.facing:GonkVec3{0,0,1};}
void load_world(const std::string& path){
 imported_world.load(path);imported=true;
 world.user=&imported_world;world.query=Gonk::World::query;
}
}
namespace Obj {
// Environmental rail ingestion only. Acquisition/movement stay in upstream rail.cpp/core.
class GonkRailLoader {
public:
 static void load(CRailManager& manager) {
  std::vector<Gonk::Rail> defaults={{{{test_rail[0][0],test_rail[0][1],test_rail[0][2]},{test_rail[1][0],test_rail[1][1],test_rail[1][2]}},test_rail_terrain}};
  const auto& rails=Headless::imported ? Headless::imported_world.rails:defaults;
  int count=0;for(const auto& rail:rails)count+=rail.points.size();
  manager.Cleanup();manager.m_num_nodes=count;manager.m_current_node=count;
  if(!count)return;
  manager.mp_nodes=static_cast<CRailNode*>(calloc(count,sizeof(CRailNode)));
  if(!manager.mp_nodes) throw std::bad_alloc();
  int offset=0;
  for(const auto& rail:rails){
   for(size_t i=0;i<rail.points.size();++i){
    auto& node=manager.mp_nodes[offset+i];auto a=rail.points[i],b=i+1<rail.points.size() ? rail.points[i+1]:a;
    node.m_pos.Set(a.x,a.y,a.z);node.m_node=offset+i;node.m_terrain_type=rail.terrain;node.m_flags.ClearAll();node.SetActive(true);
    node.m_BBMin.Set(std::min(a.x,b.x),std::min(a.y,b.y),std::min(a.z,b.z));
    node.m_BBMax.Set(std::max(a.x,b.x),std::max(a.y,b.y),std::max(a.z,b.z));
   }
   for(size_t i=0;i+1<rail.points.size();++i)manager.NewLink(&manager.mp_nodes[offset+i],&manager.mp_nodes[offset+i+1]);
   offset+=rail.points.size();
  }
 }
};
void CSkaterFlipAndRotateComponent::RefreshFromStructure(Script::CStruct* p){InitFromStructure(p);}
CSkaterFlipAndRotateComponent::CSkaterFlipAndRotateComponent(){SetType(CRC_SKATERFLIPANDROTATE);}
CSkaterFlipAndRotateComponent::~CSkaterFlipAndRotateComponent(){}
void CSkaterFlipAndRotateComponent::InitFromStructure(Script::CStruct*){}
void CSkaterFlipAndRotateComponent::Update(){}
void CSkaterFlipAndRotateComponent::Finalize(){}
void CSkaterFlipAndRotateComponent::GetDebugInfo(Script::CStruct*){}
CBaseComponent::EMemberFunctionResult CSkaterFlipAndRotateComponent::CallMemberFunction(uint32,Script::CStruct*,Script::CScript*){Headless::unsupported("flip/rotate command");}
void CSkaterFlipAndRotateComponent::DoAnyFlipRotateOrBoardRotateAfters(){
 Headless::called("FlipRotateAfters:no-animation");
 if(mFlipAfter || mRotateAfter || mBoardRotateAfter) Headless::unsupported("pending animation rotation");
}
bool CTrickComponent::TriggerAnyExtraGrindTrick(bool,bool,bool,bool){Headless::called("ExtraGrindTrick:none-configured");return false;}
}
namespace Mdl {
Obj::CRailManager* Skate::GetRailManager(){static Obj::CRailManager manager;return &manager;}
}
namespace Headless {
void enable_rails(){
 if(!imported){static GonkThugMeshWorld mesh={test_triangles,sizeof(test_triangles)/sizeof(test_triangles[0]),1};world.user=&mesh;world.query=gonk_thug_mesh_query;}
 rails_enabled=true;Obj::GonkRailLoader::load(*Mdl::Skate::Instance()->GetRailManager());
}
void clear_environment(){
 Mdl::Skate::Instance()->GetRailManager()->Cleanup();
 imported_world=Gonk::World{};imported=false;rails_enabled=false;
 world={GONK_THUG_COLLISION_ABI_VERSION,nullptr,gonk_thug_flat_plane_query};
 extern uint64 frame,collisions,lookups;
 extern std::map<std::string,uint64> peripheral;
 frame=collisions=lookups=0;peripheral.clear();
}
}
// Preserve original do_grind_trick's table selection. The script VM is not
// executed: this profile records the selected animation/trick script explicitly.
namespace Script {
#include "grind_table.inc"
static CArray main_array,sub_arrays[9];
CArray::CArray(){m_type=ESYMBOLTYPE_NONE;m_size=0;m_union=0;}
CArray::~CArray(){}
CArray* GetArray(uint32 id,EAssertType){
 if(id==0x2ab3341d) return &main_array;
 Headless::unsupported("script array lookup");
}
CArray* CArray::GetArray(uint32 index) const {
 if(this==&main_array && index<9) return &sub_arrays[index];
 Headless::unsupported("nested script array");
}
uint32 CArray::GetChecksum(uint32 index) const {
 for(int i=0;i<9;++i) if(this==&sub_arrays[i] && index<16) return Headless::checksum(grind_table[i][index]);
 Headless::unsupported("grind table index");
}
static std::map<const CScript*,uint32> selected;
CScript::CScript(){mp_params=nullptr;}
CScript::~CScript(){selected.erase(this);}
void CScript::SetScript(uint32 id,CStruct*,Obj::CObject*) {
 for(auto& row:grind_table) for(auto name:row) if(Headless::checksum(name)==id) {selected[this]=id;Headless::called((std::string("SelectedGrindScript:")+name).c_str());return;}
 Headless::unsupported("script execution outside grind presentation profile");
}
EScriptReturnVal CScript::Update(){
 if(!selected.count(this)) Headless::unsupported("unknown script update");
 Headless::called("GrindScript:presentation-only-no-balance");return ESCRIPTRETURNVAL_FINISHED;
}
}
