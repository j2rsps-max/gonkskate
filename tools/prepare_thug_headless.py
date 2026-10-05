"""Generate a case-sensitive headless build view; never edit the source checkout."""
import argparse
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('upstream', type=Path)
parser.add_argument('output', type=Path)
a = parser.parse_args()
for p in (a.upstream / 'Code').rglob('*'):
    if not p.is_file() or p.suffix.lower() not in ('.h', '.inl', '.cpp'): continue
    rel = str(p.relative_to(a.upstream / 'Code')).lower()
    text = p.read_text(encoding='latin-1')
    text = re.sub(r'(#\s*include\s*[<"])([^>"\n]+)',
                  lambda m: m[1] + m[2].replace('\\', '/').lower(), text)
    text = text.replace('(##A)', '(A)')
    text = re.sub(r'(\b(\w+)<\s*_T\s*>\s*::)\2<\s*_T\s*>', r'\1\2', text)
    text = re.sub(r'(\b(\w+)<\s*_V\s*>\s*::)\2<\s*_V\s*>', r'\1\2', text)
    if p.suffix.lower() == '.h':
        text = re.sub(r'friend\s+([A-Za-z_]\w*(?:::\w+)?)\s*;', r'friend class \1;', text)
    if rel == 'sk/engine/rectfeeler.h':
        text = text.replace('isnanf(', 'std::isnan(')
    if rel == 'gel/scripting/script.h':
        text = text.replace('friend CScript *GetNextScript(CScript *p_script=NULL);', 'friend CScript *GetNextScript(CScript *p_script);')
    if rel == 'gel/soundfx/soundfx.h':
        text = text.replace('#elif defined( __PLAT_WN32__ )', '#elif defined( __PLAT_WN32__ ) || defined(__PLAT_GONK__)')
    if rel == 'sk/objects/skater.h':
        start = text.index('class  CSkater :')
        brace = text.index('{', start)
        depth, end = 1, brace + 1
        while depth:
            depth += (text[end] == '{') - (text[end] == '}')
            end += 1
        end = text.index(';', end) + 1
        replacement = (Path(__file__).resolve().parents[1] / 'native/thug_adapter/headless/skater_class.h').read_text()
        text = text[:start] + replacement + text[end:]
        text = text.replace('defined(__PLAT_XBOX__) || defined(__PLAT_WN32__)',
                            'defined(__PLAT_XBOX__) || defined(__PLAT_WN32__) || defined(__PLAT_GONK__)')
    if rel == 'core/list/head.h':
        text = text.replace('public:', 'public:\n    using Node<_T>::GetNext;\n    using Node<_T>::GetPrev;\n    using Node<_T>::InList;\n    using Node<_T>::node_init;\n    using Node<_T>::vHEAD_NODE;\n    using Priority = typename Node<_T>::Priority;', 1)
    if rel == 'core/allmath.h':
        text = text.replace('#ifndef __PLAT_WN32__', '#if !defined(__PLAT_WN32__) && !defined(__PLAT_GONK__)')
    if rel == 'sys/mem/memman.h':
        text = text.replace('#if defined(__PLAT_WN32__)\n\t\treturn _msize(pAddr);',
                            '#if defined(__PLAT_GONK__)\n\t\treturn gonk_alloc_size(pAddr);\n#elif defined(__PLAT_WN32__)\n\t\treturn _msize(pAddr);')
    if rel == 'core/defines.h':
        marker = '#ifdef __PLAT_WN32__\ntypedef long'
        assert marker in text
        types = '''#ifdef __PLAT_GONK__
typedef int32_t int32;
typedef uint32_t uint32;
typedef int32_t sint32;
typedef int64_t int64;
typedef uint64_t uint64;
typedef int64_t sint64;
#endif
'''
        text = text.replace(marker, types + marker, 1)
        text = text.replace('#define __CORE_DEFINES_H', '#define __CORE_DEFINES_H\n#include <cstdint>\n#include <cstddef>\n#include <cstdio>\n#include <cstdlib>\n#include <cstring>\n#include <cmath>\n#include <iostream>\n#include <climits>\n#include <malloc.h>\n#ifdef _WIN32\ninline size_t gonk_alloc_size(void* p) { return _msize(p); }\n#else\ninline size_t gonk_alloc_size(void* p) { return malloc_usable_size(p); }\n#endif\ntypedef const char* LPCSTR;\nnamespace Obj { class CCompositeObject; }', 1)
    if rel == 'core/thread.h':
        text = text.replace('#ifdef __PLAT_WN32__', '#if defined(__PLAT_WN32__) || defined(__PLAT_GONK__)')
    out = a.output / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
overrides = Path(__file__).resolve().parents[1] / 'native/thug_adapter/headless/overrides'
for p in overrides.rglob('*.h'):
    out = a.output / p.relative_to(overrides)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(p.read_text())
print('Generated headless build view:', a.output)
