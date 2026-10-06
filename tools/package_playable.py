"""Package tracked cumulative sources with the verified Windows preview tools."""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--godot-archive',type=Path,required=True)
p.add_argument('--output',type=Path)
a=p.parse_args()
expected='266978b803f7532edc69bdd5d8c4fdced0ea97aef1224a8879616398a2559e135520e186add06b532aa92bdfeecf6ac024634024de4b3abd69f6c34e6d6d0563'
assert hashlib.sha512(a.godot_archive.read_bytes()).hexdigest()==expected,'Godot archive hash differs from official 4.4.1 SHA512 sums'
manifest_path=root/'build/thug-headless-windows/manifest.json';manifest=json.loads(manifest_path.read_text())
exe=root/'build/thug-headless-windows/gonkskate-thug-test.exe'
assert hashlib.sha256(exe.read_bytes()).hexdigest()==manifest['executable_sha256']
assert manifest['upstream_commit']=='98b4e24921446ccd4b157453e25697f9574f0053'
assert manifest.get('runtime_world_version')==1,'Package requires runtime world loading'
checks=json.loads((root/'logs/thug-headless-windows/summary.json').read_text())
assert checks['soak_landings']==55 and checks['rail_ticks']==49
world_checks=json.loads((root/'logs/world-import-windows/summary.json').read_text())
assert world_checks['passed'] and not world_checks['retail_assets_used']
hub_checks=json.loads((root/'logs/hub-integration-summary.json').read_text())
hub_selftest=json.loads((root/'logs/milestone-self-test-summary.json').read_text())
area_checks=json.loads((root/'logs/area-check-windows-v070/summary.json').read_text())
ui_checks=json.loads((root/'logs/hub-ui-summary.json').read_text())
contacts=json.loads((root/'logs/geometry-contacts-windows/summary.json').read_text())
recovery=json.loads((root/'logs/recovery-windows-summary.json').read_text())
launcher_failure=json.loads((root/'logs/recovery-launcher-summary.json').read_text())
workshop=json.loads((root/'logs/workshop-windows/summary.json').read_text())
client=json.loads((root/'logs/client-features-windows/summary.json').read_text())
assert hub_checks['passed'] and hub_checks['fixture_capture_pipeline'] and not hub_checks['retail_assets_used']
assert area_checks['passed'] and area_checks['deterministic']
assert ui_checks['passed'] and ui_checks['responsive_during_worker']
assert contacts['passed'] and contacts['executable_sha256']==manifest['executable_sha256']
assert len(contacts['cases'])==4 and all(case['replay_equal'] and case['reset_passed'] for case in contacts['cases'].values())
assert recovery['passed'] and recovery['retained_failure_report'] and launcher_failure['passed']
assert workshop['passed'] and workshop['editor_ui_and_controller'] and workshop['saved_copy']
assert workshop['authentic_rail_ticks']==20 and workshop['replay_equal'] and workshop['reset_passed']
assert workshop['executable_sha256']==manifest['executable_sha256']
assert client['passed'] and all(case['passed'] for case in client['cases'].values())
assert hub_checks['workshop_saved_copy_pipeline']
assert hub_selftest['workshop_checks']['passed'] and hub_selftest['client_checks']['passed']
assert hub_selftest['exit_code']==0 and all(stage['exit_code']==0 for stage in hub_selftest['stages'])
assert hashlib.sha256((root/'worlds/test_area.json').read_bytes()).hexdigest()==manifest['world_sha256']
files=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
version=(root/'VERSION').read_text().strip();prefix='GonkSkate-v'+version+'/'
assert hub_checks['version']==version and hub_selftest['version']==version and ui_checks['version']==version
assert workshop['version']==version and client['version']==version and launcher_failure['version']==version
if a.output is None:a.output=root.parent/f'GonkSkate-v{version}-Windows-Playable-Full-Package.zip'
skate_exe=root/'build/skate3-input-windows/gonkskate-skate3-input-test.exe'
skate_manifest=json.loads((skate_exe.parent/'manifest.json').read_text())
assert hashlib.sha256(skate_exe.read_bytes()).hexdigest()==skate_manifest['executable_sha256']
source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
 bundle.writestr(prefix+'RELEASE_INFO.json',json.dumps({'version':version,'source_commit':source_commit,'upstream_commit':manifest['upstream_commit'],'skate3_commit':skate_manifest['skate3'],'skate3_sdk_commit':skate_manifest['sdk'],'godot_version':'4.4.1','runtime_world_version':1,'entry_point':'GONKSKATE.cmd','windows_validation':'Windows Godot/native workshop picking/controller/rail/replay, session counters, fall reset and recovery under Wine. New owner workshop validation pending.','hub_validation':'Linux responsive full workflow; actual workshop child -> saved variant -> real THUG acceptance -> asset-free export','retail_skate_capture_validated':True,'retail_capture_scope':'Owner v0.7.1 area: 857 render triangles, deterministic standing ollie/landing, 1308 interactive ticks, 12 landings, no native stops; zero original rails.','user_authored_rails':True,'live_thug_control_of_skate_guest':False},indent=2)+'\n')
 for name in files:
  if name:bundle.write(root/name,prefix+name)
 for name in ['build/thug-headless-windows/gonkskate-thug-test.exe','build/thug-headless-windows/manifest.json',
              'build/skate3-input-windows/gonkskate-skate3-input-test.exe','build/skate3-input-windows/manifest.json',
              'logs/thug-headless/summary.json','logs/thug-headless-windows/summary.json',
              'logs/world-import-windows/summary.json','logs/playable-preview.png',
              'logs/milestone-self-test-summary.json','logs/area-check-windows-v070/summary.json',
              'logs/hub-integration-summary.json','logs/hub-ui-summary.json','logs/hub-preview.png',
              'logs/geometry-contacts-windows/summary.json','logs/recovery-windows-summary.json',
              'logs/recovery-launcher-summary.json','logs/workshop-windows/summary.json',
              'logs/client-features-windows/summary.json','logs/workshop-preview.png']:
  bundle.write(root/name,prefix+name)
 with zipfile.ZipFile(a.godot_archive) as engine:
  for name in engine.namelist():
   assert Path(name).name==name
   bundle.writestr(prefix+'bin/godot/'+name,engine.read(name))
print(a.output)
print('SHA256',hashlib.sha256(a.output.read_bytes()).hexdigest())
print('Bytes',a.output.stat().st_size)
