#include "gonkskate_thug_collision.h"
#include <cmath>
#include <initializer_list>
extern "C" uint8_t gonk_thug_flat_plane_query(void*,const GonkThugCollisionQuery* q,GonkThugCollisionHit* hit) {
    if(!q || !hit) return 0;
    for(float value:{q->start.x,q->start.y,q->start.z,q->end.x,q->end.y,q->end.z})
        if(!std::isfinite(value)) return 0;
    const uint16_t flags=GONK_THUG_FACE_SKATABLE;
    if((flags&q->ignore_1) || ((~flags)&q->ignore_0)) return 0;
    const float dy=q->end.y-q->start.y;
    if(dy==0) return 0;
    const float fraction=-q->start.y/dy;
    if(fraction<0 || fraction>1) return 0;
    *hit={};
    hit->point={q->start.x+(q->end.x-q->start.x)*fraction,0,q->start.z+(q->end.z-q->start.z)*fraction};
    hit->normal={0,1,0};hit->fraction=fraction;hit->flags=flags;hit->terrain=GONK_THUG_TERRAIN_CONCRETE_SMOOTH;
    return 1;
}
