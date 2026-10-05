#include "gonkskate_thug_mesh.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>
void check(bool v,const char* n){if(!v){fprintf(stderr,"FAILED %s\n",n);exit(1);}}
int main(){
 GonkThugTriangle triangles[]={{{{-5,3,-5},{-5,3,5},{5,3,-5}},1,3},{{{-5,7,-5},{-5,7,5},{5,7,-5}},2,4}};
 GonkThugMeshWorld world={triangles,2,1};
 GonkThugCollisionQuery q={{-1,10,-1},{-1,-10,-1},0,0,0};GonkThugCollisionHit h;
 check(gonk_thug_mesh_query(&world,&q,&h) && h.point.y==7 && h.terrain==4,"nearest elevated triangle");
 check(h.normal.y==1 && h.fraction==0.15f,"normal and segment fraction");
 q.farthest=1;check(gonk_thug_mesh_query(&world,&q,&h) && h.point.y==0,"farthest includes floor");
 q.farthest=0;q.ignore_1=2;check(gonk_thug_mesh_query(&world,&q,&h) && h.point.y==3,"mask filtering before nearest");
 q.ignore_1=0;q.ignore_0=2;check(gonk_thug_mesh_query(&world,&q,&h) && h.point.y==7,"required flag");
 q.ignore_0=0;q.start.x=q.end.x=20;check(gonk_thug_mesh_query(&world,&q,&h) && h.point.y==0,"outside triangle uses floor");
 world.floor=0;check(!gonk_thug_mesh_query(&world,&q,&h),"outside triangle misses without floor");
 q.start={-1,2,-1};q.end={-1,8,-1};check(gonk_thug_mesh_query(&world,&q,&h) && h.point.y==3 && h.normal.y==1,"two sided triangle keeps world normal");
 q.start.y=5;q.end.y=6;check(!gonk_thug_mesh_query(&world,&q,&h),"finite segment excludes surfaces");
 GonkThugTriangle slope={{{0,0,0},{0,4,4},{4,0,0}},1,1};world={&slope,1,0};q={{1,10,1},{1,-10,1},0,0,0};
 check(gonk_thug_mesh_query(&world,&q,&h) && std::abs(h.point.y-1)<0.00001f,"slope contact");
 check(std::abs(h.normal.y-0.70710678f)<0.00001f && h.normal.z<0,"slope normal");
 world={nullptr,1,0};check(!gonk_thug_mesh_query(&world,&q,&h),"null triangle storage rejected");
 puts("PASS nearest/farthest, masks, finite segment, triangle bounds and slope normal");
}
