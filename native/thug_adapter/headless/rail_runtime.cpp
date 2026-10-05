#include <sk/objects/rail.h>
#include <gonkskate_thug_mesh.h>
#include "test_world.inc"
#include <sk/modules/skate/skate.h>
#include <sk/components/skaterflipandrotatecomponent.h>
#include <gel/components/trickcomponent.h>
#include <gel/scripting/array.h>
#include <gel/scripting/script.h>
#include <map>
#include <string>
namespace Headless {void called(const char*);[[noreturn]] void unsupported(const char*);uint32 checksum(const char*);bool rails_enabled=false;extern GonkThugCollisionApi world;}
namespace Obj {
// Environmental rail ingestion only. Acquisition/movement stay in upstream rail.cpp/core.
class GonkRailLoader {
public:
 static void load(CRailManager& manager) {
  manager.Cleanup();manager.m_num_nodes=2;manager.m_current_node=2;
  manager.mp_nodes=static_cast<CRailNode*>(calloc(2,sizeof(CRailNode)));
  if(!manager.mp_nodes) throw std::bad_alloc();
  for(int i=0;i<2;++i) {
   auto& node=manager.mp_nodes[i];node.m_pos.Set(test_rail[i][0],test_rail[i][1],test_rail[i][2]);
   node.m_node=i;node.m_terrain_type=test_rail_terrain;node.m_flags.ClearAll();node.SetActive(true);
   node.m_BBMin.Set(test_rail[0][0],test_rail[0][1],test_rail[0][2]);node.m_BBMax.Set(test_rail[1][0],test_rail[1][1],test_rail[1][2]);
  }
  manager.NewLink(&manager.mp_nodes[0],&manager.mp_nodes[1]);
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
void enable_rails(){static GonkThugMeshWorld mesh={test_triangles,sizeof(test_triangles)/sizeof(test_triangles[0]),1};world.user=&mesh;world.query=gonk_thug_mesh_query;rails_enabled=true;Obj::GonkRailLoader::load(*Mdl::Skate::Instance()->GetRailManager());}
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
