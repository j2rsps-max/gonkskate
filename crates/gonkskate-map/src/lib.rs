use serde::Deserialize;
use std::{fs, path::Path};

#[derive(Debug, Clone, Copy, Deserialize)]
pub struct Vec3 {
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SpawnPoint {
    pub name: String,
    pub position: Vec3,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Rail {
    pub name: String,
    pub points: Vec<Vec3>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct GonkMap {
    pub name: String,
    pub source_game: String,
    pub spawns: Vec<SpawnPoint>,
    #[serde(default)]
    pub rails: Vec<Rail>,
}

impl GonkMap {
    pub fn load(path: impl AsRef<Path>) -> Result<Self, Box<dyn std::error::Error>> {
        let text = fs::read_to_string(path)?;
        Ok(toml::from_str(&text)?)
    }

    pub fn primary_spawn(&self) -> &SpawnPoint {
        self.spawns
            .first()
            .expect("map must contain at least one spawn point")
    }
}
