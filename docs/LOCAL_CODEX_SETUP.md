# Continue in the existing local Codex project

The owner already has a Codex project pointing at `Z:\Games\GonkSkate`.
Keep that project. Its parent folder holds the game and test-package folders;
the Git source checkout will be a separate `Source` child.

## First checkout

1. Open Windows PowerShell. The current PowerShell folder does not matter because
   the command below supplies the full destination path.
2. If `Z:\Games\GonkSkate\Source` does not already exist, paste this command and
   press Enter:

   ```powershell
   git clone --single-branch --branch main https://github.com/j2rsps-max/gonkskate.git "Z:\Games\GonkSkate\Source"
   ```

   Git downloads the source and creates `Source` automatically. The source-only
   branch choice avoids fetching the separate historical release archives.
   Cloning the public repository does not require a GitHub sign-in. Wait until
   the `PS ...>` prompt returns.
3. Verify the checkout:

   ```powershell
   git -C "Z:\Games\GonkSkate\Source" status
   ```

   A fresh checkout should report `On branch main` and `working tree clean`.
   `Source` should contain `Cargo.toml`, `crates`, `native`, `docs`,
   `CODEX_HANDOFF.md` and `CODEX_START_PROMPT.txt`.
4. Open the existing GonkSkate project in Codex and start its first chat. Tell
   Codex to work from `Z:\Games\GonkSkate\Source` and read the handoff there.
   The project itself can stay pointed at the parent folder.
5. Paste the contents of `Source\CODEX_START_PROMPT.txt`, or begin with:

   ```text
   Continue GonkSkate from Z:\Games\GonkSkate\Source. My Codex project points
   at its parent Z:\Games\GonkSkate; use Source as the working repository.
   Read CODEX_HANDOFF.md, docs/CURRENT_CHECKPOINT.md and CODEX_START_PROMPT.txt
   from Source, then continue the existing project without restarting it.
   THUG is installed in its existing sibling game folder. Inspect its actual
   local paths. The inventory found loose meshes/textures and skeleton/animation
   PRE archives; verify and adapt those formats before importing a character.
   ```

## If something differs

- If `Source` already exists, run the verification command first. An existing
  source checkout does not need another clone. Preserve any edits before updating.
- If PowerShell says `git` is not recognized, verify Git for Windows is installed,
  then reopen PowerShell. Return the exact error if it remains unavailable.
- If cloning fails, return the error text. Do not delete or overwrite existing
  game, package or source folders to retry.
- Local Codex needs an active local execution environment for Windows file
  inspection. If the new chat is using cloud execution, it cannot see `Z:`;
  it can work on the GitHub source and metadata while the local run supplies tests.

## What the next local chat knows

Owner inventory `GonkSkate-thug-files-results-20261007-163554-841393.zip`
completed with 6,829 files, no scan errors or limits. It found 635 `.skin`,
812 `.tex`, zero loose `.ske`/`.ska` and 182 archive-name candidates. Relevant
paths within the selected THUG folder include `Game/Data/pre/skeletons.pre`,
`anims.pre`, `netanims.pre`, `unloadableanims.pre` and `skaterparts.pre`.
These are filename/size observations, not decoded format or character-pair
validation. The local agent should inspect the archives and original loader
before implementing a bounded extractor. Original assets stay on the PC.

After local or cloud changes, inspect Git status and synchronize through GitHub.
The public install page remains a later release task, documented in the roadmap.
