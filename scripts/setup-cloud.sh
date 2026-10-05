#!/usr/bin/env bash
set -euo pipefail
# Keep tools outside the project; isolated cloud tasks use this existing checkout.
mkdir -p /workspace/tooling
if [ ! -x /workspace/tooling/python/bin/python3 ]; then
    python3 -m venv /workspace/tooling/python
fi
/workspace/tooling/python/bin/pip install --disable-pip-version-check cmake==4.4.4 ninja==1.13.2
export RUSTUP_HOME=/workspace/tooling/rustup
export CARGO_HOME=/workspace/tooling/cargo
export PATH=/workspace/tooling/cargo/bin:/workspace/tooling/python/bin:$PATH
if [ ! -x /workspace/tooling/cargo/bin/rustup ]; then
    curl --fail --location https://sh.rustup.rs -o /workspace/tooling/rustup-init.sh
    sh /workspace/tooling/rustup-init.sh -y --no-modify-path --profile minimal --default-toolchain 1.99.0
else
    rustup toolchain install 1.99.0 --profile minimal
    rustup default 1.99.0
fi
cd /workspace/gonkskate
if [ ! -e external/kisak-thug ]; then
    git clone --depth 1 https://github.com/SwagSoftware/kisak-thug.git external/kisak-thug
    git -C external/kisak-thug fetch --depth 1 origin 98b4e24921446ccd4b157453e25697f9574f0053
    git -C external/kisak-thug checkout --detach 98b4e24921446ccd4b157453e25697f9574f0053
fi
# Do not reset or update a user's existing reference checkout.
python3 scripts/test-all.py
