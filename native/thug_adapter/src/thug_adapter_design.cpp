/*
 * Design scaffold only.
 *
 * This file deliberately does not copy THUG source code.
 * It documents the exact mapping we will implement against a locally supplied
 * kisak-thug checkout.
 */

#include "../include/gonkskate_thug.h"

/*
THUG integration targets discovered in kisak-thug:

Code/Sk/Components/SkaterCorePhysicsComponent.{h,cpp}

    CSkaterCorePhysicsComponent::Update()

Private state-specific simulation:
    do_on_ground_physics()
    do_in_air_physics()
    do_wallride_physics()
    do_wallplant_physics()
    do_lip_physics()
    do_rail_physics()

Important transition/helper paths:
    do_jump()
    snap_to_ground()
    handle_forward_collision()
    handle_forward_collision_in_air()
    check_side_collisions()
    check_for_wallride()
    check_for_wallplant()
    maybe_spine_transfer()
    maybe_acid_drop()
    maybe_stick_to_rail()
    will_take_rail()
    got_rail()
    skate_off_rail()

World collision:
    Code/Sk/Engine/feeler.{h,cpp}
    CFeeler::GetCollision(...)
    CFeeler::GetMovableCollision(...)

Collision caching:
    Nx::CCollCache / Nx::CCollCacheManager

Authoritative transform/state:
    GetObject()->m_pos
    GetObject()->m_old_pos
    GetObject()->m_vel
    GetObject()->m_matrix

The first real adapter should preserve the THUG component/state machine and
replace only the world-query boundary.  That avoids "recreating" THUG physics.
*/
