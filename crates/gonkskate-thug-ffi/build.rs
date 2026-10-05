fn main() {
    let adapter = std::path::Path::new("../../native/thug_adapter");
    for path in ["src/thug_params.cpp", "src/thug_scripted_stats.inc", "include/gonkskate_thug_params.h"] {
        println!("cargo:rerun-if-changed={}", adapter.join(path).display());
    }
    cc::Build::new()
        .cpp(true)
        .std("c++17")
        .include(adapter.join("include"))
        .file(adapter.join("src/thug_params.cpp"))
        .compile("gonkskate_thug_parameters");
}
