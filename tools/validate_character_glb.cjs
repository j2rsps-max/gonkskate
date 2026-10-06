// Independent Khronos glTF validation. Install gltf-validator separately;
// it is development tooling and is not required on the owner's PC.
const fs = require('node:fs');
const path = require('node:path');

async function main() {
  const [library, input, output] = process.argv.slice(2);
  if (!library || !input || !output) throw new Error('Pass validator module path, GLB path and report path');
  const validator = require(path.resolve(library));
  const report = await validator.validateBytes(new Uint8Array(fs.readFileSync(input)), {
    uri: path.basename(input), maxIssues: 1000
  });
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({errors: report.issues.numErrors, warnings: report.issues.numWarnings,
    infos: report.issues.numInfos, validatorVersion: report.validatorVersion}));
  if (report.issues.numErrors || report.issues.numWarnings) process.exitCode = 1;
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
