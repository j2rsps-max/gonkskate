#![allow(non_camel_case_types)]

use core::ffi::c_void;

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct GonkVec3 {
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct GonkThugInput {
    pub left_x: f32,
    pub left_y: f32,
    pub right_x: f32,
    pub right_y: f32,
    pub ollie: u8,
    pub grind: u8,
    pub grab: u8,
    pub flip: u8,
    pub revert: u8,
    pub spine: u8,
}

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct GonkThugPlayerState {
    pub position: GonkVec3,
    pub velocity: GonkVec3,
    pub up: GonkVec3,
    pub forward: GonkVec3,
    pub state: i32,
    pub rail_node: i32,
    pub terrain: u32,
    pub switched: u8,
    pub landed_this_frame: u8,
}

pub type RaycastFn = unsafe extern "C" fn(
    user: *mut c_void,
    start: GonkVec3,
    end: GonkVec3,
    hit_point: *mut GonkVec3,
    hit_normal: *mut GonkVec3,
    terrain: *mut u32,
    flags: *mut u32,
) -> u8;

pub type FindRailFn = unsafe extern "C" fn(
    user: *mut c_void,
    start: GonkVec3,
    end: GonkVec3,
    rail_id: *mut i32,
    nearest_point: *mut GonkVec3,
    tangent: *mut GonkVec3,
) -> u8;

#[repr(C)]
#[derive(Clone, Copy)]
pub struct GonkThugWorldApi {
    pub user: *mut c_void,
    pub raycast: Option<RaycastFn>,
    pub find_rail: Option<FindRailFn>,
}

/// Synthetic flat-floor implementation used by the first native bring-up test.
/// The plane is y=0 with an upward normal.
///
/// This is intentionally tiny: when the real THUG adapter calls a collision
/// query, we can prove the callback boundary works before loading any game map.
pub unsafe extern "C" fn flat_plane_raycast(
    _user: *mut c_void,
    start: GonkVec3,
    end: GonkVec3,
    hit_point: *mut GonkVec3,
    hit_normal: *mut GonkVec3,
    terrain: *mut u32,
    flags: *mut u32,
) -> u8 {
    let dy = end.y - start.y;

    if dy.abs() < f32::EPSILON {
        return 0;
    }

    let t = -start.y / dy;
    if !(0.0..=1.0).contains(&t) {
        return 0;
    }

    if !hit_point.is_null() {
        *hit_point = GonkVec3 {
            x: start.x + (end.x - start.x) * t,
            y: 0.0,
            z: start.z + (end.z - start.z) * t,
        };
    }

    if !hit_normal.is_null() {
        *hit_normal = GonkVec3 { x: 0.0, y: 1.0, z: 0.0 };
    }

    // Temporary normalized terrain 0 = generic concrete.
    if !terrain.is_null() {
        *terrain = 0;
    }
    if !flags.is_null() {
        *flags = 0;
    }

    1
}

pub unsafe extern "C" fn no_rails(
    _user: *mut c_void,
    _start: GonkVec3,
    _end: GonkVec3,
    _rail_id: *mut i32,
    _nearest_point: *mut GonkVec3,
    _tangent: *mut GonkVec3,
) -> u8 {
    0
}

pub fn synthetic_flat_world() -> GonkThugWorldApi {
    GonkThugWorldApi {
        user: core::ptr::null_mut(),
        raycast: Some(flat_plane_raycast),
        find_rail: Some(no_rails),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn raycast_hits_flat_plane() {
        let mut point = GonkVec3::default();
        let mut normal = GonkVec3::default();
        let mut terrain = u32::MAX;
        let mut flags = u32::MAX;

        let hit = unsafe {
            flat_plane_raycast(
                core::ptr::null_mut(),
                GonkVec3 { x: 2.0, y: 5.0, z: 3.0 },
                GonkVec3 { x: 2.0, y: -5.0, z: 3.0 },
                &mut point,
                &mut normal,
                &mut terrain,
                &mut flags,
            )
        };

        assert_eq!(hit, 1);
        assert!((point.y - 0.0).abs() < 0.0001);
        assert!((normal.y - 1.0).abs() < 0.0001);
    }
}
