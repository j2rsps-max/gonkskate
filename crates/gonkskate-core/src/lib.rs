use gonkskate_map::GonkMap;
use gonkskate_physics_api::{InputFrame, PhysicsBackend, PlayerState};

pub struct Runtime {
    map: GonkMap,
    backend: Box<dyn PhysicsBackend>,
    player: PlayerState,
}

impl Runtime {
    pub fn new(map: GonkMap, mut backend: Box<dyn PhysicsBackend>) -> Self {
        let spawn = map.primary_spawn();
        let player = PlayerState::at(spawn.position);
        backend.on_map_loaded(&map);

        Self { map, backend, player }
    }

    pub fn tick(&mut self, dt: f32, input: &InputFrame) {
        self.backend.step(dt, &self.map, input, &mut self.player);
    }

    pub fn player(&self) -> &PlayerState {
        &self.player
    }

    pub fn backend_name(&self) -> &'static str {
        self.backend.name()
    }

    pub fn map_name(&self) -> &str {
        &self.map.name
    }
}
