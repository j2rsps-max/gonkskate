"""Compile upstream's exact method locally; upstream code stays in build/."""
import argparse
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('upstream', type=Path)
parser.add_argument('--cxx', default='c++')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
build = root / 'build/stat-differential'
build.mkdir(parents=True, exist_ok=True)
text = (args.upstream / 'Code/Sk/Objects/skater.cpp').read_text()
start = text.index('float\tCSkater::GetScriptedStat(Script::CStruct *pSS)')
brace = text.index('{', start)
depth, end = 1, brace+1
while depth:
    depth += (text[end] == '{') - (text[end] == '}')
    end += 1
(build / 'upstream_get_scripted_stat.inc').write_text(text[start:end] + '\n')
exe = build / 'stat-differential'
subprocess.run([args.cxx, '-std=c++17', '-I'+str(build),
                '-I'+str(root / 'native/thug_adapter/include'),
                str(root / 'native/thug_adapter/tests/upstream_stat_fixture.cpp'),
                str(root / 'native/thug_adapter/src/thug_params.cpp'), '-o', str(exe)], check=True)
subprocess.run([str(exe)], check=True)
