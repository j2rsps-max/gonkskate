"""Persistent local map library and asset-free milestone sessions for the hub."""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path

from gonk_world import encode, load
from import_map import convert

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PREFIXES = ('GonkSkate-playable-results-', 'GonkSkate-skate3-check-results-',
                   'GonkSkate-skate3-capture-results-', 'GonkSkate-skate3-reference-results-')


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class Library:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.path = self.root / 'user/hub.json'
        self.data = {'schema_version': 1, 'skate_executable': '', 'maps': []}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if data.get('schema_version') != 1 or not isinstance(data.get('maps'), list):
                raise ValueError('Unsupported hub settings; preserve user/hub.json for diagnosis')
            self.data = data
        for item in self.data['maps']:
            self.map_path(item)

    def map_path(self, item):
        if item.get('id') == 'courtyard':
            return self.root / 'worlds/courtyard.json'
        path = (self.root / item['path']).resolve()
        if not path.is_relative_to(self.root / 'local-worlds'):
            raise ValueError('Library map must remain under local-worlds')
        return path

    def maps(self):
        return [{'id': 'courtyard', 'name': 'Gonk courtyard', 'source': 'Original demo',
                 'triangles': 8, 'rails': 2}, *self.data['maps']]

    def save(self):
        save_json(self.path, self.data)

    def link_skate(self, path):
        path = Path(path).resolve()
        if not path.is_file():
            raise ValueError('Choose the installed Skate3Recomp executable')
        self.data['skate_executable'] = str(path)
        self.save()

    def import_map(self, source, **options):
        world = convert(source, **options)
        target = self.root / 'local-worlds' / ('map-' + uuid.uuid4().hex + '.json')
        save_json(target, world)
        return self.register(target)

    def register(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.root / 'local-worlds'):
            raise ValueError('Captured maps must stay in local-worlds')
        world = load(path)
        for item in self.data['maps']:
            if self.map_path(item) == path:
                return item
        item = {'id': uuid.uuid4().hex, 'path': str(path.relative_to(self.root)),
                'name': world.get('name', path.stem),
                'source': 'Skate capture' if world.get('source_game') == 'skate3-render-capture' else 'Imported geometry',
                'triangles': len(world['triangles']), 'rails': len(world['rails'])}
        self.data['maps'].append(item)
        self.data['selected_map'] = item['id']
        self.save()
        return item

    def record_check(self, item, report):
        if item['id'] == 'courtyard':
            self.data['courtyard_check'] = report
        else:
            stored = next(row for row in self.data['maps'] if row['id'] == item['id'])
            stored['last_check'] = report
        self.save()


def discover_skate(downloads=None):
    # Bounded discovery in the owner's Downloads folder, not a disk-wide scan.
    base = Path(downloads) if downloads else Path.home() / 'Downloads'
    if not base.is_dir():
        return []
    result = []
    pending = [(base, 0)]
    visited = 0
    while pending and visited < 500:
        directory, depth = pending.pop()
        visited += 1
        try:
            children = list(directory.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_symlink():
                continue
            if child.is_file() and child.name.lower() in ['skate3.exe', 'skate3']:
                result.append(child.resolve())
            elif child.is_dir() and depth < 3 and not child.name.startswith('.'):
                pending.append((child, depth + 1))
    return sorted(set(result))


def safe_diagnostic_bundle(path):
    denied = ('.iso', '.xex', '.xexp', '.gsnap', '.buffers.bin', '.scene.jsonl', '.gonkworld', '.obj', '.fbx', '.png', '.dds', '.pak')
    with zipfile.ZipFile(path) as source:
        if sum(item.file_size for item in source.infolist()) > 256 * 1024 * 1024:
            raise ValueError('Diagnostic bundle exceeds 256 MiB')
        for item in source.infolist():
            name = item.filename.replace('\\', '/').lower()
            if name.endswith(denied) or Path(name).name in ['selected-world.json', 'world.json']:
                raise ValueError('Diagnostic bundle contains local world/game data; export blocked')
            if name.startswith('/') or '..' in Path(name).parts or item.file_size > 128 * 1024 * 1024:
                raise ValueError('Invalid diagnostic bundle entry')
            if Path(name).suffix not in ['.json', '.jsonl', '.csv', '.txt', '.log']:
                raise ValueError('Unexpected diagnostic file type; export blocked')
            if name.endswith('.json'):
                value = json.loads(source.read(item).decode('utf-8-sig'))
                if isinstance(value, dict) and isinstance(value.get('triangles'), list):
                    raise ValueError('Diagnostic bundle contains geometry; export blocked')


class Session:
    def __init__(self, action, root=ROOT, progress=None):
        self.root = Path(root).resolve()
        self.directory = self.root / 'logs' / ('milestone-' + stamp())
        self.directory.mkdir(parents=True)
        self.progress = progress or (lambda message: None)
        self.bundles = []
        self.report = {'schema_version': 1, 'action': action, 'stages': [], 'exit_code': 0,
                       'version': (self.root / 'VERSION').read_text().strip(),
                       'retail_assets_in_report': False}

    def run(self, label, command, timeout=None):
        logs = self.root / 'logs'
        record = {'name': label, 'exit_code': None}
        self.report['stages'].append(record)
        log = self.directory / (f'{len(self.report["stages"]):02d}-' + label + '.txt')
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        started = time.monotonic()
        self.progress('Running: ' + label.replace('-', ' '))
        try:
            with log.open('w', encoding='utf-8') as output:
                creation = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                process = subprocess.Popen(list(map(str, command)), cwd=self.root, env=env,
                                           stdout=output, stderr=subprocess.STDOUT, creationflags=creation)
                try:
                    while process.poll() is None:
                        if timeout is not None and time.monotonic() - started > timeout:
                            process.kill()
                            process.wait()
                            raise TimeoutError(f'{label} exceeded {timeout} seconds')
                        time.sleep(0.1)
                    record['exit_code'] = process.returncode
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
        finally:
            record['seconds'] = round(time.monotonic() - started, 2)
            # Use only bundles reported by this child. Other hub instances may
            # be writing unrelated results in the same logs folder.
            if log.is_file():
                with log.open(encoding='utf-8', errors='replace') as output:
                    for line in output:
                        if line.startswith('Result bundle: '):
                            path = Path(line.removeprefix('Result bundle: ').strip()).resolve()
                            if path.parent != logs.resolve() or not path.name.startswith(BUNDLE_PREFIXES) or path.suffix != '.zip':
                                raise ValueError('Child reported an invalid diagnostic bundle path')
                            safe_diagnostic_bundle(path)
                            if path not in self.bundles:
                                self.bundles.append(path)
        if record['exit_code']:
            raise RuntimeError(f'{label} failed (exit {record["exit_code"]}); see the milestone results')
        self.progress('Passed: ' + label.replace('-', ' '))

    def finish(self, error=None):
        if error is not None:
            self.report.update(exit_code=1, error=str(error))
        save_json(self.directory / 'report.json', self.report)
        output = self.root / 'logs' / ('GonkSkate-milestone-results-' + self.directory.name.removeprefix('milestone-') + '.zip')
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(self.directory / 'report.json', 'report.json')
            for log in self.directory.glob('*.txt'):
                archive.write(log, 'stages/' + log.name)
            for name in ['summary.json', 'native.txt', 'trace.csv']:
                path = self.directory / 'area-check' / name
                if path.is_file():
                    archive.write(path, 'area-check/' + name)
            for path in self.bundles:
                safe_diagnostic_bundle(path)
                archive.write(path, 'checks/' + path.name)
        return output


class Hub:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.library = Library(root)

    def native(self):
        native = self.root / ('build/thug-headless-windows/gonkskate-thug-test.exe'
                              if os.name == 'nt' else 'build/thug-headless/gonkskate-thug-test')
        manifest = json.loads((native.parent / 'manifest.json').read_text(encoding='utf-8'))
        if manifest.get('runtime_world_version') != 1 or hashlib.sha256(native.read_bytes()).hexdigest() != manifest['executable_sha256']:
            raise ValueError('Native executable differs from its manifest. Extract the full release package again.')
        return native

    def area_check(self, session, item):
        from test_imported_area import check
        session.progress('Checking real THUG spawn, ollie, landing and replay')
        directory = session.directory / 'area-check'
        try:
            return check(self.library.map_path(item), self.native(), directory)
        finally:
            summary = directory / 'summary.json'
            if summary.is_file():
                report = json.loads(summary.read_text(encoding='utf-8'))
                session.report['area_check'] = report
                self.library.record_check(item, report)

    def capture_result(self, session):
        for bundle in reversed(session.bundles):
            if bundle.name.startswith('GonkSkate-skate3-capture-results-'):
                with zipfile.ZipFile(bundle) as archive:
                    report = json.loads(archive.read('report.json'))
                filename = report.get('world_filename')
                if filename:
                    if Path(filename).name != filename or not filename.startswith('skate3-area-') or not filename.endswith('.json'):
                        raise ValueError('Invalid capture result filename')
                    item = self.library.register(self.root / 'local-worlds' / filename)
                    session.report['map'] = item.copy()
                    if 'area_check' in report:
                        self.library.record_check(item, report['area_check'])
                    return item
        return None

    def execute(self, action, *, item=None, source=None, options=None, progress=None, launch=True):
        """All public actions produce a single result ZIP, including failed stages."""
        session = Session(action, self.root, progress)
        error = None
        try:
            if action == 'self-test':
                self.area_check(session, self.library.maps()[0])
                session.run('wall-and-edge-contacts', [sys.executable, 'tools/test_geometry_contacts.py',
                            '--executable', self.native(), '--output', session.directory / 'contacts'], timeout=180)
                session.report['contact_checks'] = json.loads((session.directory / 'contacts/summary.json').read_text(encoding='utf-8'))
                session.run('thug-controller-integration', [sys.executable, 'scripts/run-playable.py',
                            '--world', 'worlds/courtyard.json', '--controller-autotest'], timeout=300)
                session.run('skate-sdk-controller-integration', [sys.executable, 'scripts/run-skate3-check.py',
                            '--autotest'], timeout=300)
            elif action == 'play-skate':
                exe = self.library.data.get('skate_executable')
                if not exe:
                    raise ValueError('Link your installed Skate3Recomp executable first')
                session.run('original-skate', [sys.executable, 'scripts/run-skate3-reference.py', '--exe', exe])
            elif action == 'controller-lab':
                session.run('physical-controller-lab', [sys.executable, 'scripts/run-skate3-check.py'])
            elif action == 'capture':
                command = [sys.executable, 'scripts/run-skate3-capture.py', '--no-play']
                if source:
                    command += ['--scene', str(source)]
                else:
                    exe = self.library.data.get('skate_executable')
                    if not exe:
                        raise ValueError('Link your installed Skate3Recomp executable first')
                    command += ['--exe', exe]
                try:
                    session.run('skate-area-capture', command)
                finally:
                    item = self.capture_result(session)
            elif action in ['import', 'check', 'play-thug']:
                if action == 'import':
                    item = self.library.import_map(source, **(options or {}))
                if item is None:
                    raise ValueError('Select a map first')
                session.report['map'] = item.copy()
                self.area_check(session, item)
            else:
                raise ValueError('Unknown hub action')
            if launch and action in ['capture', 'import', 'play-thug']:
                if item is None:
                    raise ValueError('Capture completed without an imported map')
                session.run('thug-on-selected-map', [sys.executable, 'scripts/run-playable.py',
                            '--world', self.library.map_path(item)])
        except Exception as failure:
            error = failure
            session.progress('Check failed: ' + str(failure))
        bundle = session.finish(error)
        if action == 'self-test':
            save_json(self.root / 'logs/milestone-self-test-summary.json', session.report)
        session.progress('Results saved: ' + str(bundle))
        return {'passed': error is None, 'error': str(error) if error else None,
                'bundle': str(bundle), 'report': session.report}
