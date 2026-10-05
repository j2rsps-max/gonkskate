#!/usr/bin/env python3
"""Portable readiness checks. Logs and a ZIP survive a failed native command."""
import datetime
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
LOG = ROOT / 'logs' / STAMP
LOG.mkdir(parents=True)
results = []


def run(name, argv):
    print(f'[{name}] {" ".join(map(str, argv))}', flush=True)
    with (LOG / (name + '.txt')).open('w') as output:
        process = subprocess.run(list(map(str, argv)), cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
    results.append({'stage': name, 'exit_code': process.returncode})
    if process.returncode:
        raise RuntimeError(f'{name} exited {process.returncode}; see {LOG / (name+".txt")}')


failed = False
try:
    # Exercise stderr capture with success, and nonzero exit propagation separately.
    run('stderr-selftest', [sys.executable, '-c', 'import sys; print("STDOUT_OK"); print("STDERR_OK", file=sys.stderr)'])
    assert all(x in (LOG / 'stderr-selftest.txt').read_text() for x in ('STDOUT_OK','STDERR_OK'))
    probe = subprocess.run([sys.executable, '-c', 'import sys; sys.exit(7)'])
    assert probe.returncode == 7
    run('rust-tests', ['cargo', 'test', '--workspace', '--locked'])
    build = ROOT / 'build/native-smoke'
    run('native-configure', ['cmake', '-S', ROOT / 'native/smoke', '-B', build])
    run('native-build', ['cmake', '--build', build, '--config', 'Release', '--parallel', '2'])
    run('native-tests', ['ctest', '--test-dir', build, '-C', 'Release', '--output-on-failure'])
    smoke = build / 'gonkskate_abi_smoke'
    if sys.platform == 'win32':
        smoke = next(build.rglob('gonkskate_abi_smoke.exe'))
    run('abi-smoke', [smoke])
    run('q-parser-tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_thug_q.py', '-v'])
    upstream = ROOT / 'external/kisak-thug'
    if not upstream.exists():
        run('thug-clone', ['git', 'clone', '--depth', '1', 'https://github.com/SwagSoftware/kisak-thug.git', upstream])
    commit = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    (LOG / 'kisak-thug-commit.txt').write_text(commit+'\n')
    paths = ['Sk/Components/SkaterCorePhysicsComponent.cpp', 'Sk/Components/SkaterCorePhysicsComponent.h',
             'Sk/Components/SkaterStateComponent.cpp', 'Sk/Components/SkaterPhysicsControlComponent.cpp',
             'Sk/Components/SkaterRotateComponent.cpp', 'Sk/Engine/feeler.cpp', 'Sk/Engine/feeler.h', 'Sk/Objects/skater.cpp']
    for path in paths:
        if not (upstream / 'Code' / path).is_file(): raise RuntimeError('Missing upstream source: '+path)
    core = (upstream / 'Code/Sk/Components/SkaterCorePhysicsComponent.cpp').read_text()
    for symbol in ['CSkaterCorePhysicsComponent::Update', 'do_on_ground_physics', 'do_in_air_physics',
                   'do_wallride_physics','do_wallplant_physics','do_lip_physics','do_rail_physics',
                   'maybe_stick_to_rail','got_rail']:
        if symbol not in core: raise RuntimeError('Missing upstream symbol: '+symbol)
    (LOG / 'source-validation.txt').write_text('PASS\n')
    run('captured-stats', [sys.executable, 'tools/extract_thug_stats.py', upstream, '--check'])
    run('parameter-comparison', [sys.executable, 'tools/compare_thug_params.py', ROOT, LOG])
    if sys.platform != 'win32':
        run('upstream-stat-differential', [sys.executable, 'tools/test_thug_stat_semantics.py', upstream])
    else:
        results.append({'stage':'upstream-stat-differential','status':'unrun: standalone helper currently uses GNU/Clang command syntax'})
    comparison = json.loads((LOG / 'thug-param-compare.json').read_text())
    results.append({'stage':'active-parameter-coverage', 'status':'WARN' if comparison['mismatch_count'] else 'PASS',
                    'mismatches':comparison['mismatches']})
    for map_name in ('test_thug', 'test_skate3'):
        for physics in ('thug', 'skate3'):
            run(f'host-{map_name}-{physics}', ['cargo','run','--locked','-p','gonkskate-app','--',
                                             '--map',f'maps/{map_name}.toml','--physics',physics])
except Exception as error:
    failed = True
    results.append({'error':str(error)})
    print(error, file=sys.stderr)
finally:
    (LOG / 'summary.json').write_text(json.dumps({'development_checks':'FAIL' if failed else 'PASS',
        'authentic_ground_air':'NOT IMPLEMENTED', 'results':results}, indent=2)+'\n')
    version = (ROOT / 'VERSION').read_text().strip()
    bundle = ROOT / 'logs' / f'GonkSkate-{version}-results-{STAMP}.zip'
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in LOG.iterdir(): archive.write(p, p.name)
    print('Result bundle:', bundle)
sys.exit(1 if failed else 0)
