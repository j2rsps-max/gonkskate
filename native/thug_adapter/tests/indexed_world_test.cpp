#include "gonkskate_world.h"
#include <random>
#include <cstdio>
#include <cstdlib>
#include <cmath>

void check(bool condition,const char* message){if(!condition){fprintf(stderr,"FAILED %s\n",message);exit(1);}}
int main(){
 Gonk::World indexed;indexed.floor=true;
 // Overlapping geometry, duplicate contacts, varied flags/terrain and slopes
 // catch candidate ordering, nearest/farthest and broad-phase edge errors.
 for(int x=-10;x<10;++x)for(int z=-10;z<10;++z){
  float a=x*20,b=z*20,y=(x+z)%3*5+30;
  indexed.triangles.push_back({{{a,y,b},{a,y+3,b+20},{a+20,y,b}},uint16_t(1+((x+z+20)%3)),uint16_t(1+((x+z+20)%4))});
 }
 auto duplicate=indexed.triangles.front();duplicate.terrain=59;
 indexed.triangles.push_back(duplicate);indexed.build_index();
 GonkThugMeshWorld linear{indexed.triangles.data(),uint32_t(indexed.triangles.size()),1};
 std::mt19937 rng(4106);std::uniform_real_distribution<float> p(-250,250);
 for(int i=0;i<15000;++i){
  GonkThugCollisionQuery q{{p(rng),p(rng),p(rng)},{p(rng),p(rng),p(rng)},uint16_t(i%4),uint16_t((i/4)%4),uint8_t(i%2)};
  GonkThugCollisionHit a{},b{};auto first=gonk_thug_mesh_query(&linear,&q,&a),second=Gonk::World::query(&indexed,&q,&b);
  check(first==second,"indexed hit/miss differs from exhaustive query");
  if(first)check(a.fraction==b.fraction&&a.point.x==b.point.x&&a.point.y==b.point.y&&a.point.z==b.point.z&&a.normal.y==b.normal.y&&a.flags==b.flags&&a.terrain==b.terrain,"indexed contact differs from exhaustive query");
 }
 for(auto vertex:indexed.triangles.front().vertices){
  GonkThugCollisionQuery q{{vertex.x,100,vertex.z},{vertex.x,-100,vertex.z},0,0,0};GonkThugCollisionHit a{},b{};
  check(gonk_thug_mesh_query(&linear,&q,&a)==Gonk::World::query(&indexed,&q,&b)&&a.fraction==b.fraction,"vertex boundary query");
 }
 // Different terrain makes identical-face tie ordering observable.
 indexed.floor=false;linear.floor=0;
 auto vertex=indexed.triangles.front().vertices[0];
 GonkThugCollisionQuery tied{{vertex.x+5,100,vertex.z+5},{vertex.x+5,-100,vertex.z+5},0,0,0};
 GonkThugCollisionHit tied_hit{};
 check(Gonk::World::query(&indexed,&tied,&tied_hit)&&tied_hit.terrain==indexed.triangles.front().terrain,"original face wins identical-contact tie");
 puts("PASS indexed world: 15000 exhaustive comparisons, flags, contact ties and boundaries");
}
