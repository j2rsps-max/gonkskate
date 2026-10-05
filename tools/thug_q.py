"""Small, fail-closed reader for physics.q declarations (not a Q interpreter)."""
import re

NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
PAIR = re.compile(r'\(\s*(' + NUMBER + r')\s*,\s*(' + NUMBER + r')\s*\)')


def uncomment(text):
    # Match in source order so a decorative /* inside a // line cannot
    # swallow live declarations up to the next block-comment terminator.
    return re.sub(r"//[^\n]*|;[^\n]*|/\*.*?\*/",
                  lambda m: "\n" * m.group().count("\n"), text, flags=re.S)



def declarations(text):
    """Read immediate declarations only; nested structures remain opaque."""
    result = {}
    pos = 0
    pattern = re.compile(r'\s*([A-Za-z_]\w*)\s*=\s*')
    while pos < len(text):
        match = pattern.match(text, pos)
        if not match:
            if text[pos:].strip():
                raise ValueError('Unsupported Q declaration: ' + text[pos:pos+80])
            break
        name = match[1].lower()
        start = match.end()
        if text[start:start+1] in ('{', '['):
            opening = text[start]
            closing = '}' if opening == '{' else ']'
            depth = 1
            end = start + 1
            while end < len(text) and depth:
                depth += (text[end] == opening) - (text[end] == closing)
                end += 1
            if depth:
                raise ValueError('Unclosed structure: ' + name)
            value = text[start:end]
        else:
            end = text.find('\n', start)
            if end < 0:
                end = len(text)
            value = text[start:end].strip()
        if name in result:
            raise ValueError('Duplicate declaration: ' + name)
        result[name] = value
        pos = end
    return result


def physics_tables(text):
    globals_ = declarations(uncomment(text))
    skating = declarations(globals_['skater_physics'][1:-1])
    return globals_, skating


def lookup(name, globals_, skating):
    key = name.lower()
    return skating[key] if key in skating else globals_[key]


def stat_definition(raw, globals_):
    if not raw.startswith('{') or not raw.endswith('}'):
        raise ValueError('Expected stat structure: ' + raw)
    body = raw[1:-1].strip()
    pair = PAIR.match(body)
    if not pair:
        raise ValueError('Missing unnamed range: ' + raw)
    result = {'low': float(pair[1]), 'high': float(pair[2]), 'stat_index': -1}
    body = body[pair.end():].strip()
    while body:
        stat = re.match(r'STATS_\w+\b', body, re.I)
        field = re.match(r'(switch|diff|limit)\s*=\s*', body, re.I)
        if stat:
            result['stat_index'] = int(globals_[stat[0].lower()])
            body = body[stat.end():].strip()
        elif field:
            key = field[1].lower()
            body = body[field.end():]
            if key == 'limit':
                number = re.match(NUMBER, body)
                if not number:
                    raise ValueError('Invalid limit: ' + body)
                result[key] = float(number[0]); body = body[number.end():].strip()
            else:
                pair = PAIR.match(body)
                if pair:
                    result[key] = [float(pair[1]), float(pair[2])]
                    body = body[pair.end():].strip()
                else:
                    alias = re.match(r'\w+', body)
                    if not alias:
                        raise ValueError('Invalid pair reference: ' + body)
                    pair = PAIR.fullmatch(globals_[alias[0].lower()])
                    if not pair:
                        raise ValueError('Invalid referenced pair: ' + alias[0])
                    result[key] = [float(pair[1]), float(pair[2])]
                    body = body[alias.end():].strip()
        else:
            raise ValueError('Unsupported stat field: ' + body)
    return result
