#include "gonkskate_thug_mesh.h"
#include <cmath>
#include <initializer_list>
static GonkVec3 sub(GonkVec3 a,GonkVec3 b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
static GonkVec3 cross(GonkVec3 a,GonkVec3 b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
static float dot(GonkVec3 a,GonkVec3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
extern "C" uint8_t gonk_thug_mesh_query(void* user,const GonkThugCollisionQuery* q,GonkThugCollisionHit* out){
 if(!user || !q || !out) return 0;
 auto& world=*static_cast<const GonkThugMeshWorld*>(user);
 if(world.count && !world.triangles) return 0;
 for(auto v:{q->start,q->end}) if(!std::isfinite(v.x)||!std::isfinite(v.y)||!std::isfinite(v.z)) return 0;
 bool found=world.floor && gonk_thug_flat_plane_query(nullptr,q,out);
 auto direction=sub(q->end,q->start);
 for(uint32_t i=0;i<world.count;++i){
  auto& face=world.triangles[i];
  if((face.flags&q->ignore_1)||((~face.flags)&q->ignore_0)) continue;
  auto e1=sub(face.vertices[1],face.vertices[0]),e2=sub(face.vertices[2],face.vertices[0]);
  auto p=cross(direction,e2);float determinant=dot(e1,p);
  if(std::abs(determinant)<1e-8f) continue;
  auto start=sub(q->start,face.vertices[0]);float u=dot(start,p)/determinant;
  auto k=cross(start,e1);float v=dot(direction,k)/determinant;
  if(u<-1e-6f||v<-1e-6f||u+v>1.000001f) continue;
  float t=dot(e2,k)/determinant;
  if(t<0||t>1 || (found && (q->farthest ? t<=out->fraction:t>=out->fraction))) continue;
  auto normal=cross(e1,e2);float length=std::sqrt(dot(normal,normal));
  if(length==0) continue;
  *out={};out->fraction=t;out->flags=face.flags;out->terrain=face.terrain;
  out->normal={normal.x/length,normal.y/length,normal.z/length};
  out->point={q->start.x+direction.x*t,q->start.y+direction.y*t,q->start.z+direction.z*t};found=true;
 }
 return found;
}
