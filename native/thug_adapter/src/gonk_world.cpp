#include "gonkskate_world.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <numeric>
#include <stdexcept>

namespace {
float axis(GonkVec3 v,int i){return i==0 ? v.x : i==1 ? v.y : v.z;}
struct Reader {
 std::ifstream input;
 explicit Reader(const std::string& path):input(path,std::ios::binary){if(!input)throw std::runtime_error("Cannot open world");}
 uint32_t word(){unsigned char b[4];if(!input.read(reinterpret_cast<char*>(b),4))throw std::runtime_error("Truncated world");return uint32_t(b[0])|(uint32_t(b[1])<<8)|(uint32_t(b[2])<<16)|(uint32_t(b[3])<<24);}
 float scalar(){uint32_t bits=word();float f;std::memcpy(&f,&bits,4);if(!std::isfinite(f)||std::abs(f)>10000000)throw std::runtime_error("Invalid world coordinate");return f;}
 GonkVec3 vector(){float x=scalar(),y=scalar(),z=scalar();return {x,y,z};}
};
bool bounds(GonkVec3 low,GonkVec3 high,const GonkThugCollisionQuery& q){
 double near=0,far=1;
 for(int i=0;i<3;++i){
  double s=axis(q.start,i),d=double(axis(q.end,i))-s;
  double pad=0.001+3e-6*(double(axis(high,i))-axis(low,i));
  if(d==0){if(s<axis(low,i)-pad || s>axis(high,i)+pad)return false;continue;}
  double a=(axis(low,i)-pad-s)/d,b=(axis(high,i)+pad-s)/d;
  if(a>b)std::swap(a,b);near=std::max(near,a);far=std::min(far,b);if(near>far)return false;
 }
 return true;
}
}
namespace Gonk {
void World::load(const std::string& path){
 Reader r(path);char magic[8];if(!r.input.read(magic,8)||std::memcmp(magic,"GNKWLD1\0",8))throw std::runtime_error("Invalid world magic");
 if(r.word()!=1)throw std::runtime_error("Unsupported world version");
 auto count=r.word(),rail_count=r.word(),has_floor=r.word();
 if(count>300000 || rail_count>16383 || has_floor>1)throw std::runtime_error("Invalid world counts");
 World next;next.floor=has_floor;next.spawn=r.vector();next.facing=r.vector();
 float length=std::hypot(next.facing.x,next.facing.z);
 if(std::abs(next.facing.y)>1e-6f||length<1e-6f)throw std::runtime_error("Invalid spawn direction");
 next.facing={next.facing.x/length,0,next.facing.z/length};
 next.triangles.reserve(count);
 for(uint32_t i=0;i<count;++i){
  GonkThugTriangle t{};for(auto& v:t.vertices)v=r.vector();auto meta=r.word();t.flags=meta&65535;t.terrain=meta>>16;
  if(t.terrain>59)throw std::runtime_error("Invalid terrain");
  auto a=t.vertices[0],b=t.vertices[1],c=t.vertices[2];
  double x=(double(b.y)-a.y)*(double(c.z)-a.z)-(double(b.z)-a.z)*(double(c.y)-a.y);
  double y=(double(b.z)-a.z)*(double(c.x)-a.x)-(double(b.x)-a.x)*(double(c.z)-a.z);
  double z=(double(b.x)-a.x)*(double(c.y)-a.y)-(double(b.y)-a.y)*(double(c.x)-a.x);
  if(x*x+y*y+z*z<1e-12)throw std::runtime_error("Degenerate world triangle");next.triangles.push_back(t);
 }
 uint32_t total=0;
 for(uint32_t i=0;i<rail_count;++i){
  auto points=r.word(),terrain=r.word();if(points<2||points>32767||total+points>32767||terrain>59)throw std::runtime_error("Invalid rail");
  total+=points;Rail rail;rail.terrain=terrain;
  for(uint32_t j=0;j<points;++j){auto p=r.vector();if(j){auto b=rail.points.back();if(p.x==b.x&&p.y==b.y&&p.z==b.z)throw std::runtime_error("Zero-length rail");}rail.points.push_back(p);}
  next.rails.push_back(std::move(rail));
 }
 if(r.input.peek()!=std::char_traits<char>::eof())throw std::runtime_error("Trailing world data");
 if(!count&&!has_floor)throw std::runtime_error("World has no collision");
 next.build_index();*this=std::move(next);
}
void World::build_index(){
 nodes_.clear();order_.resize(triangles.size());std::iota(order_.begin(),order_.end(),0u);
 if(!order_.empty())build_node(0,order_.size());
}
uint32_t World::build_node(uint32_t first,uint32_t count){
 Node node{{INFINITY,INFINITY,INFINITY},{-INFINITY,-INFINITY,-INFINITY},first,count,0,0};
 for(uint32_t i=first;i<first+count;++i)for(auto v:triangles[order_[i]].vertices){
  node.low={std::min(node.low.x,v.x),std::min(node.low.y,v.y),std::min(node.low.z,v.z)};
  node.high={std::max(node.high.x,v.x),std::max(node.high.y,v.y),std::max(node.high.z,v.z)};
 }
 uint32_t id=nodes_.size();nodes_.push_back(node);
 if(count>8){
  int split=0;for(int i=1;i<3;++i)if(axis(node.high,i)-axis(node.low,i)>axis(node.high,split)-axis(node.low,split))split=i;
  auto center=[&](uint32_t t){auto& v=triangles[t].vertices;return (double(axis(v[0],split))+axis(v[1],split)+axis(v[2],split))/3;};
  auto middle=first+count/2;
  std::nth_element(order_.begin()+first,order_.begin()+middle,order_.begin()+first+count,[&](uint32_t a,uint32_t b){auto x=center(a),y=center(b);return x!=y ? x<y:a<b;});
  auto left=build_node(first,count/2),right=build_node(middle,count-count/2);
  nodes_[id].count=0;nodes_[id].left=left;nodes_[id].right=right;
 }
 return id;
}
uint8_t World::query(void* user,const GonkThugCollisionQuery* q,GonkThugCollisionHit* out){
 if(!user||!q||!out)return 0;
 for(auto v:{q->start,q->end})if(!std::isfinite(v.x)||!std::isfinite(v.y)||!std::isfinite(v.z))return 0;
 auto& world=*static_cast<World*>(user);bool found=world.floor&&gonk_thug_flat_plane_query(nullptr,q,out);
 uint32_t winner=0;bool floor_wins=found;
 std::vector<uint32_t> pending;if(!world.nodes_.empty())pending.push_back(0);
 while(!pending.empty()){
  auto node=world.nodes_[pending.back()];pending.pop_back();if(!bounds(node.low,node.high,*q))continue;
  if(!node.count){pending.push_back(node.right);pending.push_back(node.left);continue;}
  for(uint32_t i=node.first;i<node.first+node.count;++i){
   uint32_t index=world.order_[i];GonkThugMeshWorld leaf{&world.triangles[index],1,0};GonkThugCollisionHit hit;
   if(!gonk_thug_mesh_query(&leaf,q,&hit))continue;
   bool closer=!found||(q->farthest ? hit.fraction>out->fraction:hit.fraction<out->fraction);
   bool tie=found&&hit.fraction==out->fraction&&!floor_wins&&index<winner;
   if(closer||tie){*out=hit;found=true;winner=index;floor_wins=false;}
  }
 }
 return found;
}
}
