use gonkskate_map::GonkMap;
use gonkskate_physics_api::{InputFrame, PhysicsBackend, PlayerState};

pub struct Skate3Backend {
    acceleration: f32,
    drag: f32,
    pop_speed: f32,
    gravity: f32,
}

impl Default for Skate3Backend {
    fn default() -> Self {
        Self {
            acceleration: 7.0,
            drag: 1.3,
            pop_speed: 5.5,
            gravity: 15.0,
        }
    }
}

impl PhysicsBackend for Skate3Backend {
    fn name(&self) -> &'static str { "Skate 3 prototype" }

    fn on_map_loaded(&mut self, _map: &GonkMap) {}

    fn step(
        &mut self,
        dt: f32,
        _map: &GonkMap,
        input: &InputFrame,
        player: &mut PlayerState,
    ) {
        player.velocity.x += input.move_x * self.acceleration * dt;
        player.velocity.z += input.move_y * self.acceleration * dt;

        let damping = (1.0 - self.drag * dt).max(0.0);
        player.velocity.x *= damping;
        player.velocity.z *= damping;

        if input.jump_pressed && player.grounded {
            player.velocity.y = self.pop_speed;
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
