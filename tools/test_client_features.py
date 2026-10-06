"""Real-native client checks: controller play, session counters, fall reset, recovery."""
import argparse
import json
import os
import subprocess
from pathlib import Path

from godot_runtime import godot
from gonk_world import encode, load
from project_hub import save_json

ROOT = Path(__file__).resolve().parents[1]


def check(executable, engine, output, runner=()):
    output.mkdir(parents=True, exist_ok=True)
    windows = bool(runner) and str(engine).endswith('.exe')
    def guest(path):
        value = str(Path(path).resolve())
        return 'Z:'+value if windows else value
    report = {'passed': False, 'version': (ROOT/'VERSION').read_text().strip(), 'cases': {}}
    try:
        for name in ['controller', 'fall-reset', 'recovery']:
            world = load(ROOT/'worlds/courtyard.json')
            if name=='fall-reset':
                world['rails'] = []
                world['triangles'] = world['triangles'][:2]
                for triangle in world['triangles']:
                    for v in triangle['vertices']:
                        v[0] = 300 if v[0]>0 else -300
                        v[2] = 300 if v[2]>0 else -300
            source = output/('private-'+name+'.json')
            binary = source.with_suffix('.gonkworld')
            result_file = output/(name+'-result.json')
            result_file.unlink(missing_ok=True)
            save_json(source,world)
            binary.write_bytes(encode(world))
            env = os.environ.copy()
            env.update(GONK_WORLD_JSON=guest(source), GONK_WORLD_BINARY=guest(binary),
                       GONK_THUG_EXE=guest(executable), GONK_SCENE_RESULT=guest(result_file))
            for key,subdir in [('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache')]:
                env.setdefault(key,str(ROOT/'bin/godot'/subdir))
            command = [*runner,str(engine),'--headless','--path',guest(ROOT/'playable')]
            command += ['--','--controller-autotest'] if name=='controller' else ['--script','res://test_fall_reset.gd' if name=='fall-reset' else 'res://test_recovery.gd']
            process = subprocess.run(command,env=env,capture_output=True,text=True,timeout=90,restore_signals=False)
            text = process.stdout+process.stderr
            (output/(name+'.txt')).write_text(text,encoding='utf-8')
            assert process.returncode==0,text
            health = json.loads(result_file.read_text())
            if name=='controller':
                assert 'PLAYABLE_AUTOTEST passed' in text and not health['failed']
                m = health['metrics']
                assert m['frames']==360 and m['landings']==1 and m['rail_entries']==1 and m['rail_frames']==49
                assert m['resets']==0 and m['automatic_fall_resets']==0
            elif name=='fall-reset':
                assert 'FALL_RESET_TEST passed' in text and not health['failed']
                m = health['metrics']
                assert m['frames']==400 and m['resets']==3 and m['automatic_fall_resets']==3 and m['landings']==0
            else:
                assert 'RECOVERY_TEST passed' in text and health['failed'] and health['recoveries']==2 and len(health['failures'])==2
            report['cases'][name] = {'passed': True, 'health':health}
        report['passed'] = True
    finally:
        save_json(output/'summary.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable',type=Path)
    parser.add_argument('--godot',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'logs/client-features')
    parser.add_argument('--runner',nargs='+',default=[])
    args = parser.parse_args()
    exe = args.executable or ROOT/('build/thug-headless-windows/gonkskate-thug-test.exe' if os.name=='nt' else 'build/thug-headless/gonkskate-thug-test')
    check(exe,args.godot or godot(ROOT),args.output,args.runner)
