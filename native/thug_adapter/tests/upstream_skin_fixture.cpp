// Original material/sector loader bodies are extracted into build/ by the
// differential helper. These facades replace allocation/renderer environment
// and capture Initialize inputs; the binary-read control flow is upstream.
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <vector>
#include <string>
using uint8=std::uint8_t; using uint16=std::uint16_t;
using uint32=std::uint32_t; using uint64=std::uint64_t;
using DWORD=uint32; using uint=unsigned int;
constexpr int X=0,Y=1,Z=2,W=3;
static_assert(sizeof(unsigned long)==4,"Run this fixture with the Windows file data model");
const uint8* input_end;
void memory_read(void* dst,size_t size,size_t count,uint8*& src){
    if(src>input_end || count>static_cast<size_t>(input_end-src)/size)std::abort();
    std::memcpy(dst,src,size*count);src+=size*count;
}
#define MemoryRead(dst,size,num,src) memory_read(dst,size,num,src)
#define CopyMemory(dst,src,size) std::memcpy(dst,src,size)
#define ZeroMemory(dst,size) std::memset(dst,0,size)
#define Dbg_Assert(condition) do {if(!(condition))std::abort();} while(false)
#define Dbg_MsgAssert(condition,message) Dbg_Assert(condition)
#define Dbg_Message(...) ((void)0)
#include "upstream_material_flags.inc"
namespace Image {struct RGBA {uint8 r,g,b,a;};}
using D3DCOLOR=uint32;
namespace Mth {
struct Vector {float data[4]{};Vector()=default;Vector(float a,float b,float c){data[0]=a;data[1]=b;data[2]=c;}
    float& operator[](int i){return data[i];}};
struct CBBox {void Set(const Vector&,const Vector&){} void AddPoint(const Vector&) {}};
}
namespace Mem {
struct Heap {};
struct Manager {static Manager& sHandle(){static Manager m;return m;}
    Heap* TopDownHeap(){return nullptr;} void PushContext(Heap*){} void PopContext(){}};
}
namespace Lst {
template<class T> struct HashTable {
    std::map<uint32,T*> items;explicit HashTable(uint32){}
    T* GetItem(uint32 id){auto i=items.find(id);return i==items.end()?nullptr:i->second;}
    void PutItem(uint32 id,T* item){items[id]=item;}
};
}
namespace NxXbox {struct sTexture;}
namespace Nx {struct CTexture {};struct CXboxTexture:CTexture {NxXbox::sTexture* GetEngineTexture(){std::abort();}};}
namespace NxXbox {
struct sTexture {};
struct sUVWibbleParams {float data[8];};
struct sVCWibbleKeyframe {int m_time;Image::RGBA m_color;};
static_assert(sizeof(sVCWibbleKeyframe)==8);
struct sVCWibbleParams {uint32 m_num_keyframes;int m_phase;sVCWibbleKeyframe* mp_keyframes;};
struct sTextureWibbleKeyframe {uint32 m_time;sTexture* mp_texture;};
struct sTextureWibbleParams {int m_num_keyframes[4],m_phase[4],m_num_iterations[4];sTextureWibbleKeyframe* mp_keyframes[4];};
struct sMaterial {
    static constexpr uint32 BLEND_MODE_MASK=0x00ffffff;
    uint32 m_checksum{},m_name_checksum{},m_passes{},m_flags[4]{},m_reg_alpha[4]{},m_uv_addressing[4]{},m_filtering_mode[4]{};
    uint8 m_alpha_cutoff{},m_zbias{};bool m_sorted{},m_no_bfc{},m_uv_wibble{},m_texture_wibble{};
    float m_draw_order{},m_grass_height{},m_specular_color[4]{},m_color[4][4]{},m_envmap_tiling[4][2]{},m_k[4]{};
    int m_grass_layers{},m_num_wibble_vc_anims{};
    sUVWibbleParams* mp_UVWibbleParams[4]{};sVCWibbleParams* mp_wibble_vc_params{};
    D3DCOLOR* mp_wibble_vc_colors{};sTextureWibbleParams* mp_wibble_texture_params{};sTexture* mp_tex[4]{};
};
struct sScene {Lst::HashTable<sMaterial>* pMaterialTable{};Mth::CBBox m_bbox;};
struct Captured {
    int vertices,tc_sets;uint32 material;
    std::vector<float> positions,normals,uvs;std::vector<uint32> colors,weights;
    std::vector<uint16> joints;std::vector<int> wibble;std::vector<std::vector<uint16>> lods;
};
std::vector<Captured> captured;
struct sMesh {
    static constexpr uint32 MESH_FLAG_NO_SKATER_SHADOW=2,MESH_FLAG_UNLIT=0x20000,MESH_FLAG_SHADOW_VOLUME=0x200;
    uint32 m_flags{},m_load_order{};
    void Initialize(int count,float* pos,float* norm,float* uv,int uv_count,DWORD* col,
        int lod_count,int* index_counts,uint16** indices,unsigned long material,void*,uint16* joints,uint32* weights,char* wibble){
        Captured row{};row.vertices=count;row.tc_sets=uv_count;row.material=material;
        row.positions.assign(pos,pos+count*3);
        if(norm)row.normals.assign(norm,norm+count*3);
        if(uv)row.uvs.assign(uv,uv+count*2*uv_count);
        if(col)row.colors.assign(col,col+count);
        if(joints)row.joints.assign(joints,joints+count*4);
        if(weights)row.weights.assign(weights,weights+count);
        if(wibble)for(int i=0;i<count;++i)row.wibble.push_back(wibble[i]);
        for(int i=0;i<lod_count;++i)row.lods.emplace_back(indices[i],indices[i]+index_counts[i]);
        captured.push_back(row);
    }
    void SetBoundingData(Mth::Vector&,float,Mth::Vector&,Mth::Vector&){}
    void SetBillboardData(uint32,Mth::Vector&,Mth::Vector&){std::abort();}
    void SetBoneIndex(int){}
};
void ApplyMeshScaling(float*,int){} // Disabled in the character import profile.
struct BillboardList {void AddEntry(sMesh*){std::abort();}} BillboardManager;
#include "upstream_material_loader.inc"
}
namespace Nx {
struct Scene {NxXbox::sScene* engine;NxXbox::sScene* GetEngineScene(){return engine;}};
struct InitList {uint32 count{};uint32 CountItems(){return count;}};
struct CXboxGeom {uint m_num_mesh{};Mth::CBBox m_bbox;Scene* mp_scene;InitList list;InitList* mp_init_mesh_list=&list;
    void AddMesh(NxXbox::sMesh*){++list.count;}};
struct CXboxSector {CXboxGeom* mp_geom{};uint32 m_flags{},identity{};
    void SetChecksum(uint32 value){identity=value;}bool LoadFromMemory(void**);};
void AddGrass(CXboxGeom*,NxXbox::sMesh*){} // No procedural grass in this profile.
#include "upstream_sector_loader.inc"
}
#include "upstream_weight_decode.inc"
struct StripFixture {
    int m_num_indices[1];
    std::vector<uint16> convert(std::vector<uint16>& strip){
        m_num_indices[0]=static_cast<int>(strip.size());uint16* p_index_raw=strip.data();
        std::vector<uint16> buffer(strip.size()*3);uint16* work=buffer.data();int num_edits=0;
        #include "upstream_strip.inc"
        return {buffer.begin(),buffer.begin()+num_edits*3};
    }
};
template<class T> void emit(const char* label,const std::vector<T>& values){
    std::cout<<label;for(auto value:values)std::cout<<','<<+value;std::cout<<'\n';
}
int main(int argc,char** argv){
    if(argc!=2)return 2;
    std::ifstream in(argv[1],std::ios::binary|std::ios::ate);const auto size=in.tellg();
    if(size<16 || size>128*1024*1024)return 3;
    std::vector<uint8> data(static_cast<size_t>(size));in.seekg(0);in.read(reinterpret_cast<char*>(data.data()),size);if(!in)return 4;
    input_end=data.data()+data.size();uint8* current=data.data();uint32 versions[3];
    MemoryRead(versions,sizeof(uint32),3,current);
    Lst::HashTable<Nx::CTexture> textures(2);
    auto* materials=NxXbox::LoadMaterialsFromMemory(reinterpret_cast<void**>(&current),&textures);
    std::cout<<std::setprecision(9)<<"materials_end,"<<(current-data.data())<<'\n';
    for(auto [id,material]:materials->items){
        std::cout<<"material,"<<id<<','<<material->m_name_checksum<<','<<material->m_passes<<','<<+material->m_alpha_cutoff<<'\n';
        for(uint32 i=0;i<material->m_passes;++i)std::cout<<"pass,"<<material->m_flags[i]<<','<<material->m_reg_alpha[i]<<','<<material->m_color[i][3]<<'\n';
    }
    int count;MemoryRead(&count,sizeof(int),1,current);if(count<1 || count>4096)return 5;
    NxXbox::sScene engine;engine.pMaterialTable=materials;Nx::Scene scene{&engine};
    for(int i=0;i<count;++i){Nx::CXboxGeom geom;geom.mp_scene=&scene;Nx::CXboxSector sector;sector.mp_geom=&geom;
        sector.LoadFromMemory(reinterpret_cast<void**>(&current));
        std::cout<<"sector_end,"<<(current-data.data())<<','<<sector.identity<<','<<sector.m_flags<<'\n';}
    int hierarchy;MemoryRead(&hierarchy,sizeof(int),1,current);if(hierarchy || current!=input_end)return 6;
    for(auto& row:NxXbox::captured){
        std::cout<<"mesh,"<<row.vertices<<','<<row.tc_sets<<','<<row.material<<'\n';
        emit("positions",row.positions);emit("normals",row.normals);emit("uvs",row.uvs);emit("colors",row.colors);
        emit("weights",row.weights);emit("joints",row.joints);emit("wibble",row.wibble);
        for(auto& indices:row.lods)emit("lod",indices);
        StripFixture strip;emit("triangles",strip.convert(row.lods[0]));
        for(auto decoder:{original_xbox,original_dx9})for(auto packed:row.weights){
            float weights[3];decoder(packed,weights);
            emit(decoder==original_xbox?"decode_xbox":"decode_dx9",std::vector<float>(weights,weights+3));
        }
    }
}
