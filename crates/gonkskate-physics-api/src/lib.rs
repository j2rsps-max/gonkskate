use gonkskate_map::{GonkMap, Vec3};

#[derive(Debug, Clone, Copy, Default)]
pub struct InputFrame {
    pub move_x: f32,
    pub move_y: f32,
    pub jump_pressed: bool,
    pub crouch: bool,
}

#[derive(Debug, Clone, Copy)]
pub struct PlayerState {
    pub position: Vec3,
    pub velocity: Vec3,
    pub grounded: bool,
}

impl PlayerState {
    pub fn at(position: Vec3) -> Self {
        Self {
            position,
            velocity: Vec3 { x: 0.0, y: 0.0, z: 0.0 },
            grounded: true,
        }
    }
}

pub trait PhysicsBackend: Send {
    fn name(&self) -> &'static str;
    fn on_map_loaded(&mut self, map: &GonkMap);
    fn step(
        &mut self,
        dt: f32,
        map: &GonkMap,
        input: &InputFrame,
        player: &mut PlayerState,
    );
}
