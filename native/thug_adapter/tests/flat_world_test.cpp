#include "gonkskate_thug_collision.h"
#include <cstdlib>
#include <cstdio>
#include <limits>
void check(bool value,const char* name){if(!value){fprintf(stderr,"FAILED %s\n",name);std::exit(1);}}
int main(){
 GonkThugCollisionQuery q={{2,5,3},{4,-5,7},0,0,0};GonkThugCollisionHit h;
 check(gonk_thug_flat_plane_query(nullptr,&q,&h)==1,"crossing");
 check(h.fraction==0.5f && h.point.x==3 && h.point.y==0 && h.point.z==5,"segment interpolation");
 check(h.normal.y==1 && h.flags==GONK_THUG_FACE_SKATABLE && h.terrain==GONK_THUG_TERRAIN_CONCRETE_SMOOTH,"metadata");
 check(!h.trigger && !h.movable && !h.script && !h.node_name,"static floor");
 q.ignore_1=GONK_THUG_FACE_SKATABLE;check(!gonk_thug_flat_plane_query(nullptr,&q,&h),"ignore one");
 q.ignore_1=0;q.ignore_0=2;check(!gonk_thug_flat_plane_query(nullptr,&q,&h),"required absent flag");
 q.ignore_0=GONK_THUG_FACE_SKATABLE;q.farthest=1;check(gonk_thug_flat_plane_query(nullptr,&q,&h)==1,"required present flag/far query");
 q.ignore_0=0;q.start.y=-5;q.end.y=5;check(gonk_thug_flat_plane_query(nullptr,&q,&h)==1 && h.normal.y==1,"two sided plane");
 q.start.y=5;q.end.y=2;check(!gonk_thug_flat_plane_query(nullptr,&q,&h),"outside segment");
 q.end.y=5;check(!gonk_thug_flat_plane_query(nullptr,&q,&h),"parallel");
 q.start.y=0;q.end.y=-1;check(gonk_thug_flat_plane_query(nullptr,&q,&h)==1 && h.fraction==0,"start endpoint");
 q.start.y=1;q.end.y=0;check(gonk_thug_flat_plane_query(nullptr,&q,&h)==1 && h.fraction==1,"end endpoint");
 q.start.x=std::numeric_limits<float>::quiet_NaN();check(!gonk_thug_flat_plane_query(nullptr,&q,&h),"reject nonfinite");
 check(!gonk_thug_flat_plane_query(nullptr,nullptr,&h),"null query");
 puts("PASS flat floor segment, metadata, masks, endpoint and invalid-input behavior");
}
