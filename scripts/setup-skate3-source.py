#!/usr/bin/env python3
"""Prepare pinned reference headers; preserve every pre-existing checkout."""
import json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];pin=json.loads((root/'native/skate3_adapter/config/upstream.json').read_text());checkout=root/'external/skate3'
def run(*cmd,cwd=None):subprocess.run(list(cmd),cwd=cwd,check=True)
def head(path):return subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
if not checkout.exists():
 checkout.parent.mkdir(exist_ok=True)
 run('git','clone','--depth','1','--no-checkout',pin['repository'],str(checkout))
 run('git','fetch','--depth','1','origin',pin['commit'],cwd=checkout)
 run('git','checkout','--detach',pin['commit'],cwd=checkout)
if head(checkout)!=pin['commit']:raise SystemExit('Existing Skate3 reference differs from inspected pin; left unchanged.')
sdk=checkout/'third_party/rexglue-sdk'
if (sdk/'.git').exists():
 if head(sdk)!=pin['sdk_commit']:raise SystemExit('Existing SDK differs from inspected pin; left unchanged.')
else:run('git','submodule','update','--init','--depth','1','third_party/rexglue-sdk',cwd=checkout)
assert head(sdk)==pin['sdk_commit']
# The real InputDriver includes kernel/window headers; initialize only its
# transitive header dependencies and the original InputSystem's configuration.
for name in ['simde','fmt','spdlog','tomlplusplus','sdl3','cli11']:
 path=sdk/'thirdparty'/name
 expected=subprocess.check_output(['git','-C',str(sdk),'ls-tree','HEAD','thirdparty/'+name],text=True).split()[2]
 if (path/'.git').exists():
  if head(path)!=expected:raise SystemExit(f'Existing {name} differs from SDK pin; left unchanged.')
 else:run('git','submodule','update','--init','--depth','1','thirdparty/'+name,cwd=sdk)
print('Pinned Skate3/ReXGlue driver dependencies ready; retail files are not needed for SDK tests.')
