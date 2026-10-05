use gonkskate_map::GonkMap;
use gonkskate_physics_api::{InputFrame, PhysicsBackend, PlayerState};

pub struct ThugBackend {
    move_speed: f32,
    jump_speed: f32,
    gravity: f32,
}

impl Default for ThugBackend {
    fn default() -> Self {
        Self {
            move_speed: 12.0,
            jump_speed: 8.5,
            gravity: 22.0,
        }
    }
}

impl PhysicsBackend for ThugBackend {
    fn name(&self) -> &'static str { "THUG prototype" }

    fn on_map_loaded(&mut self, _map: &GonkMap) {}

    fn step(
        &mut self,
        dt: f32,
        _map: &GonkMap,
        input: &InputFrame,
        player: &mut PlayerState,
    ) {
        player.velocity.x = input.move_x * self.move_speed;
        player.velocity.z = input.move_y * self.move_speed;

        if input.jump_pressed && player.grounded {
            player.velocity.y = self.jump_speed;
            player.grounded = false;
        }

        if !player.grounded {
            player.velocity.y -= self.gravity * dt;
        }

        player.position.x += player.velocity.x * dt;
        player.position.y += player.velocity.y * dt;
        player.position.z += player.velocity.z * dt;

        if player.position.y <= 0.0 {
            player.position.y = 0.0;
            player.velocity.y = 0.0;
            player.grounded = true;
        }
    }
}
