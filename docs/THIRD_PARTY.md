# Third-party components in the preview

The Windows preview bundles the official Godot 4.4.1 Windows engine release,
licensed under MIT; see [Godot license](licenses/GODOT_LICENSE.txt). Its original
release archive is verified against the published SHA512 sums before packaging.
The engine's built-in third-party acknowledgements are available in Godot's
editor Help / About / Third-party Licenses panel.

The native runtime is compiled against the user's research target kisak-thug,
pinned at 98b4e24921446ccd4b157453e25697f9574f0053. Upstream source is fetched
separately and kept under ignored external/; the distributed adapter sources
contain integration code and generation tooling. The binary build manifest
records the precise pin, original core hash and unresolved peripheral traps.
No retail maps, character models, textures, music or animation assets are bundled.

The Windows cross-build statically links GCC/MinGW runtime support. GCC runtime
libraries use GPLv3 with the GCC Runtime Library Exception 3.1; MinGW-w64 runtime
and headers have their upstream license notices. The corresponding notices are
included in docs/licenses/ for the compiler/runtime versions used here.
