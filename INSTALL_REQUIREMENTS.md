# Software needed for GonkSkate v0.5

The test script checks all of this automatically.

## Required

### 1. Git for Windows
Needed to retrieve the public `kisak-thug` source used as our THUG reference.

After installation, this should work in PowerShell:

```powershell
git --version
```

### 2. Rust toolchain (rustup + stable MSVC toolchain)
Install Rust using rustup.

After installation, close and reopen PowerShell and verify:

```powershell
rustup --version
rustc --version
cargo --version
rustup default stable-msvc
```

For this project, the MSVC Rust target is preferred on Windows.

### 3. Visual Studio C++ Build Tools
Install either full Visual Studio or the standalone Visual Studio Build Tools.

Select the workload:

**Desktop development with C++**

Keep the normal x64/x86 MSVC compiler and Windows SDK components selected.

### 4. CMake
CMake must be available from a new PowerShell window:

```powershell
cmake --version
```

## Recommended but not required

### Ninja
Useful later for fast native builds. v0.5 can use the Visual Studio CMake
generator, so Ninja is not mandatory.

### Python 3
The v0.5 comparison tool can use Python if available. The PowerShell test will
continue without it, but having Python 3 installed is useful for later extraction
and conversion tools.

Check with:

```powershell
python --version
```

or:

```powershell
py --version
```

## If something is already installed

Do not reinstall it. Run `RUN_FIRST_TEST.cmd`; the preflight section will tell
you exactly what is detected and what is missing.
