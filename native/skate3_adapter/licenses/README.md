# SDK test dependency notices

The standalone input-system test uses the pinned ReXGlue SDK and its header
dependencies. ReXGlue/Xenia's notice is retained in `../REXGLUE_LICENSE.txt`.
Upstream dependency license texts are retained here for {fmt}, spdlog, SIMDe,
toml++, SDL3 and CLI11. Their exact revisions are recorded in the binary's
`manifest.json`. SDL headers are used for compiling SDK declarations; no physical
SDL driver or SDL runtime library is linked into this standalone test.

These notices apply to the distributed test binaries as well as source packages.
