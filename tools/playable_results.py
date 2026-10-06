"""Judge physics-session health independently from the presentation exit code."""
import re
from pathlib import Path


def failure_message(scene_text, result=None):
    if result is not None and result.get('failed'):
        failures = result.get('failures', [])
        detail = failures[0].get('message', 'Native session failed') if failures else 'Native session failed'
        return detail + '; see the scene/session diagnostics (including any recovery)'
    stopped = re.search(r'Native process stopped at frame \d+[^\r\n]*', scene_text)
    if stopped:
        return stopped.group(0)
    return None


def session_files(scene_text, logs):
    """Collect this Godot child's declared traces, including recovery segments."""
    logs = Path(logs).resolve()
    result = []
    for line in scene_text.splitlines():
        if not line.startswith('Session trace: '):
            continue
        path = Path(line.removeprefix('Session trace: ').strip()).resolve()
        if path.parent != logs or not path.name.startswith('playable-') or path.suffix != '.csv':
            raise ValueError('Scene declared an invalid trace path')
        for suffix in ['', '.adapters.log', '.controller.jsonl']:
            file = Path(str(path) + suffix)
            if file.is_file() and file.resolve().parent == logs and file not in result:
                result.append(file)
    return result
