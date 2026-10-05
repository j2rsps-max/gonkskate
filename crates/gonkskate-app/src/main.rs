use std::env;

use gonkskate_core::Runtime;
use gonkskate_map::GonkMap;
use gonkskate_physics_api::{InputFrame, PhysicsBackend};
use gonkskate_physics_skate3::Skate3Backend;
use gonkskate_physics_thug::ThugBackend;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();

    let mut map_path = "maps/test_thug.toml".to_string();
    let mut physics = "thug".to_string();

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--map" if i + 1 < args.len() => {
                map_path = args[i + 1].clone();
                i += 2;
            }
            "--physics" if i + 1 < args.len() => {
                physics = args[i + 1].clone();
                i += 2;
            }
            _ => i += 1,
        }
    }

    let map = GonkMap::load(&map_path)?;

    let backend: Box<dyn PhysicsBackend> = match physics.as_str() {
        "thug" => Box::new(ThugBackend::default()),
        "skate3" => Box::new(Skate3Backend::default()),
        other => return Err(format!("unknown physics backend: {other}").into()),
    };

    let mut runtime = Runtime::new(map, backend);

    println!("GonkSkate");
    println!("Map: {}", runtime.map_name());
    println!("Physics: {}", runtime.backend_name());

    // Temporary deterministic test loop.
    // This is deliberately not a renderer/game loop yet.
    for frame in 0..120 {
        let input = InputFrame {
            move_x: 0.35,
            move_y: 1.0,
            jump_pressed: frame == 20,
            crouch: false,
        };
        runtime.tick(1.0 / 60.0, &input);
    }

    let p = runtime.player();
    println!(
        "Final player position: ({:.2}, {:.2}, {:.2})",
        p.position.x, p.position.y, p.position.z
    );

    Ok(())
}
