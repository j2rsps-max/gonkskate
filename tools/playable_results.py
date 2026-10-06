"""Judge physics-session health independently from the presentation exit code."""
import re


def failure_message(scene_text, result=None):
    if result is not None and result.get('failed'):
        failures = result.get('failures', [])
        detail = failures[0].get('message', 'Native session failed') if failures else 'Native session failed'
        return detail + '; see the scene/session diagnostics (including any recovery)'
    stopped = re.search(r'Native process stopped at frame \d+[^\r\n]*', scene_text)
    if stopped:
        return stopped.group(0)
    return None
