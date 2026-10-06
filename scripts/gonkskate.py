#!/usr/bin/env python3
"""GonkSkate Hub: installed Skate, local worlds and one milestone results ZIP."""
import argparse
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from project_hub import Hub, Session, discover_skate, save_json


def open_path(path):
    if os.name == 'nt':
        os.startfile(str(path))
    else:
        subprocess.Popen(['xdg-open', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def gui(hub, smoke_test=False):
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk

    window = tk.Tk()
    version = (ROOT / 'VERSION').read_text().strip()
    font_family = 'Segoe UI' if os.name == 'nt' else 'DejaVu Sans'
    window.title('GonkSkate Hub ' + version)
    window.geometry('960x680')
    window.minsize(880, 630)
    window.configure(background='#141b23')
    style = ttk.Style(window)
    style.theme_use('clam')
    style.configure('.', background='#1e2936', foreground='#e8eef5', font=(font_family, 11))
    style.configure('TNotebook.Tab', padding=(18, 10))
    style.map('TNotebook.Tab', background=[('selected', '#364d66')])
    style.configure('TButton', padding=(12, 9))
    style.map('TButton', background=[('active', '#405d79')], foreground=[('disabled', '#8492a3')])
    style.configure('TEntry', fieldbackground='#101923', foreground='#e8eef5')
    style.configure('Title.TLabel', background='#141b23', font=(font_family, 24, 'bold'))
    style.configure('Sub.TLabel', background='#141b23', foreground='#b6c8db')
    header = ttk.Frame(window, style='TFrame', padding=18)
    header.pack(fill='x')
    ttk.Label(header, text='GonkSkate', font=(font_family, 24, 'bold')).pack(anchor='w')
    ttk.Label(header, text='Your games. Your local worlds. Authentic skating.', foreground='#b6c8db').pack(anchor='w')
    tabs = ttk.Notebook(window)
    tabs.pack(fill='both', expand=True, padx=18, pady=10)
    play = ttk.Frame(tabs, padding=22)
    maps = ttk.Frame(tabs, padding=22)
    results = ttk.Frame(tabs, padding=22)
    tabs.add(play, text='Play')
    tabs.add(maps, text='Map library')
    tabs.add(results, text='Results')
    events = queue.Queue()
    controls = []
    state = {'busy': False, 'last_bundle': None, 'items': [], 'heartbeats': 0, 'test_error': None}
    status = tk.StringVar(value='Ready. Start with Run milestone check, then capture a Skate area.')
    skate_path = tk.StringVar(value=hub.library.data.get('skate_executable') or 'Skate3Recomp has not been linked yet')
    map_detail = tk.StringVar()
    capture_radius = tk.StringVar(value=f'{float(hub.library.data.get("capture_radius", 25)):g}')
    result_text = tk.Text(results, wrap='word', background='#101923', foreground='#e8eef5',
                          insertbackground='white', font=('Consolas', 10), borderwidth=0)

    def button(parent, title, command):
        widget = ttk.Button(parent, text=title, command=command)
        controls.append(widget)
        return widget

    def write(message):
        result_text.configure(state='normal')
        result_text.insert('end', message + '\n')
        result_text.see('end')
        result_text.configure(state='disabled')
        status.set(message)

    def selected():
        index = map_list.curselection()
        return state['items'][index[0]] if index else None

    def detail(event=None):
        item = selected()
        if item:
            checked = item.get('last_check') or (hub.library.data.get('courtyard_check') if item['id'] == 'courtyard' else None)
            check_status = 'Not checked yet' if not checked else ('Spawn / ollie / landing: PASSED' if checked['passed'] else 'Check failed: ' + checked.get('error', 'See Results'))
            map_detail.set(f'{item["source"]} | {item["triangles"]:,} triangles | {item["rails"]} rails\n{check_status}')

    def refresh():
        state['items'] = hub.library.maps()
        map_list.delete(0, 'end')
        for item in state['items']:
            map_list.insert('end', item['name'])
        wanted = hub.library.data.get('selected_map', 'courtyard')
        index = next((i for i, item in enumerate(state['items']) if item['id'] == wanted), 0)
        map_list.selection_set(index)
        map_list.see(index)
        detail()
        skate_path.set(hub.library.data.get('skate_executable') or 'Skate3Recomp has not been linked yet')

    def start(action, **kwargs):
        if state['busy']:
            return
        state['busy'] = True
        for control in controls:
            control.configure(state='disabled')
        write('Starting ' + action.replace('-', ' ') + '. Close the game normally when you finish.')

        def worker():
            try:
                outcome = hub.execute(action, progress=lambda message: events.put(('progress', message)), **kwargs)
            except Exception as error:
                # Preserve failures even before an action can enter its normal exporter.
                session = Session(action)
                outcome = {'passed': False, 'error': str(error), 'bundle': str(session.finish(error))}
            events.put(('done', outcome))
        threading.Thread(target=worker, daemon=True).start()

    def poll():
        state['heartbeats'] += 1
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == 'progress':
                    write(value)
                else:
                    state['busy'] = False
                    for control in controls:
                        control.configure(state='readonly' if isinstance(control, ttk.Combobox) else 'normal')
                    state['last_bundle'] = value['bundle']
                    refresh()
                    write(('PASSED. ' if value['passed'] else 'FAILED. ' + str(value['error']) + '\n') +
                          'Return this file: ' + value['bundle'])
                    if not value['passed']:
                        tabs.select(results)
                    if smoke_test:
                        passed = value['passed'] and state['heartbeats'] > 3
                        save_json(ROOT / 'logs/hub-ui-summary.json',
                                  {'passed': passed, 'version': version, 'platform': sys.platform,
                                   'responsive_during_worker': state['heartbeats'] > 3,
                                   'completed_milestone': value['passed']})
                        if not passed:
                            state['test_error'] = value['error'] or 'UI did not process events during worker'
                        window.after(100, window.destroy)
        except queue.Empty:
            pass
        window.after(100, poll)

    def link(path=None):
        path = path or filedialog.askopenfilename(title='Choose your installed Skate3Recomp executable',
                                                  filetypes=[('Skate executable', '*.exe'), ('All files', '*')])
        if path:
            try:
                hub.library.link_skate(path)
                refresh()
                write('Skate3Recomp linked. Your installed game keeps its original controls.')
            except Exception as error:
                messagebox.showerror('Could not link Skate', str(error))

    def find():
        found = discover_skate()
        if len(found) == 1:
            link(found[0])
        else:
            messagebox.showinfo('Choose Skate3Recomp', 'Choose the skate3.exe in your installed Skate3Recomp folder.\n'
                                'Found ' + str(len(found)) + ' candidates in Downloads.')
            link()

    def capture():
        radius = float(capture_radius.get())
        hub.library.data['capture_radius'] = radius
        hub.library.save()
        if not hub.library.data.get('skate_executable'):
            link()
            if not hub.library.data.get('skate_executable'):
                return
        messagebox.showinfo('Capture a Skate area',
            'Close any existing Skate3Recomp window first.\n\n'
            '1. Enter a level and stop in an open, flat area.\n'
            '2. Press F10 once. Wait for disk activity to finish.\n'
            '3. Quit Skate normally.\n\n'
            'GonkSkate checks spawn, ollie and landing, then opens the captured area with THUG physics.\n'
            'Keep several GB free. Captures and game files stay on your PC.')
        start('capture', options={'radius': radius})

    def import_map():
        source = filedialog.askopenfilename(title='Import local map geometry', filetypes=[
            ('Supported geometry', '*.obj *.json *.scene.jsonl'), ('All files', '*')])
        if not source:
            return
        options = {}
        if Path(source).suffix.lower() == '.obj':
            units = simpledialog.askstring('OBJ units', 'Source units: inch, meter or centimeter\n'
                                           'Y-up geometry; default spawn is 0, 0, 0.', initialvalue='meter')
            if units is None:
                return
            if units.strip().lower() not in ['inch', 'meter', 'centimeter']:
                messagebox.showerror('Units required', 'Enter inch, meter or centimeter.')
                return
            options['units'] = units.strip().lower()
        if source.lower().endswith('.scene.jsonl'):
            start('capture', source=source)
        else:
            start('import', source=source, options=options)

    def selected_action(action):
        item = selected()
        if item:
            hub.library.data['selected_map'] = item['id']
            hub.library.save()
            start(action, item=item)

    def set_spawn():
        from gonk_world import load
        item = selected()
        if not item:
            return
        value = simpledialog.askstring('Create map with adjusted spawn',
            'Spawn X Y Z in world inches, on a flat supporting surface.\n'
            'This creates a new library entry and preserves the existing map.',
            initialvalue=' '.join(map(str, load(hub.library.map_path(item))['spawn'])))
        if value is None:
            return
        try:
            coordinates = list(map(float, value.replace(',', ' ').split()))
            if len(coordinates) != 3:
                raise ValueError('Enter three coordinates')
        except ValueError as error:
            messagebox.showerror('Invalid spawn', str(error))
            return
        start('import', source=hub.library.map_path(item), options={'spawn_inches': coordinates}, launch=False)

    ttk.Label(play, text='1. Check this release', font=(font_family, 15, 'bold')).pack(anchor='w')
    ttk.Label(play, text='Checks authentic THUG, controller mappings and the Skate input bridge.\n'
              'The automated check uses synthetic input; test your physical controller during play.').pack(anchor='w', pady=(5, 10))
    row = ttk.Frame(play)
    row.pack(anchor='w', pady=(0, 18))
    button(row, 'Run milestone check', lambda: start('self-test')).pack(side='left', padx=(0, 8))
    button(row, 'Check my controller', lambda: start('controller-lab')).pack(side='left')
    ttk.Label(play, text='2. Link your installed Skate3Recomp', font=(font_family, 15, 'bold')).pack(anchor='w')
    ttk.Label(play, textvariable=skate_path, wraplength=810, foreground='#b6c8db').pack(anchor='w', pady=8)
    row = ttk.Frame(play)
    row.pack(anchor='w', pady=(0, 18))
    button(row, 'Find in Downloads', find).pack(side='left', padx=(0, 8))
    button(row, 'Browse executable', link).pack(side='left', padx=(0, 8))
    button(row, 'Play original Skate', lambda: start('play-skate')).pack(side='left')
    ttk.Label(play, text='3. Try THUG on a Skate area', font=(font_family, 15, 'bold')).pack(anchor='w')
    ttk.Label(play, text='Capture visible scenery, verify a flat spawn, then skate it with the THUG controller profile.\n'
              'This opens the THUG test window. Live THUG control of Skate’s own player is still pending.').pack(anchor='w', pady=(5, 10))
    row = ttk.Frame(play)
    row.pack(anchor='w')
    button(row, 'Capture Skate area and test', capture).pack(side='left', padx=(0,10))
    ttk.Label(row, text='Radius (m)').pack(side='left', padx=(0,6))
    radius_box = ttk.Combobox(row, textvariable=capture_radius, values=['25','50','100'], width=5, state='readonly')
    radius_box.pack(side='left')
    controls.append(radius_box)

    ttk.Label(maps, text='Local map library', font=(font_family, 17, 'bold')).pack(anchor='w')
    ttk.Label(maps, text='Select an area, then add rails and choose a spawn in Map workshop. Geometry stays local.').pack(anchor='w', pady=8)
    map_list = tk.Listbox(maps, background='#101923', foreground='#e8eef5', selectbackground='#466989',
                          font=(font_family, 12), height=9, exportselection=False)
    map_list.pack(fill='both', expand=True)
    map_list.bind('<<ListboxSelect>>', detail)
    ttk.Label(maps, textvariable=map_detail, wraplength=800).pack(anchor='w', pady=12)
    row = ttk.Frame(maps)
    row.pack(anchor='w')
    for title, command in [('Play with THUG', lambda: selected_action('play-thug')),
                            ('Check map', lambda: selected_action('check')), ('Import map', import_map),
                            ('Map workshop', lambda: selected_action('workshop'))]:
        button(row, title, command).pack(side='left', padx=(0, 8))
    row = ttk.Frame(maps)
    row.pack(anchor='w', pady=(8,0))
    button(row, 'Adjust spawn coordinates', set_spawn).pack(side='left')

    ttk.Label(results, text='One ZIP to return after each test', font=(font_family, 17, 'bold')).pack(anchor='w')
    ttk.Label(results, text='Results include checks and traces. ISO files, captures and imported geometry stay local.').pack(anchor='w', pady=8)
    result_text.pack(fill='both', expand=True, pady=(0, 10))
    ttk.Button(results, text='Open results folder', command=lambda: open_path(ROOT / 'logs')).pack(anchor='w')
    ttk.Label(window, textvariable=status, wraplength=920, padding=(18, 12), foreground='#b6c8db').pack(fill='x')
    refresh()
    write('GonkSkate ' + version + ' ready. Checks and game launches save one milestone-results ZIP.')
    poll()

    def close():
        if state['busy']:
            messagebox.showinfo('Test in progress', 'Close the active game normally and wait for the results ZIP before closing the hub.')
        else:
            window.destroy()
    window.protocol('WM_DELETE_WINDOW', close)
    if smoke_test:
        tabs.select(maps)
        detail()
        tabs.select(results)
        window.after(100, lambda: start('self-test'))
    window.mainloop()
    if state['test_error']:
        raise RuntimeError(state['test_error'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--self-test', action='store_true')
    action.add_argument('--scene', type=Path, help='Capture import without the GUI')
    action.add_argument('--capture', action='store_true', help='Capture using the saved Skate executable')
    action.add_argument('--check-world', type=Path, help='Check a normalized world without the GUI')
    parser.add_argument('--skate-exe', type=Path, help='Save installed Skate3Recomp executable')
    parser.add_argument('--no-play', action='store_true', help='Import/check without opening the playable test')
    parser.add_argument('--ui-smoke-test', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        hub = Hub()
        if args.skate_exe:
            hub.library.link_skate(args.skate_exe)
        if args.self_test or args.scene or args.capture or args.check_world:
            action = 'self-test' if args.self_test else 'capture' if args.scene or args.capture else 'import'
            outcome = hub.execute(action, source=args.scene or args.check_world, launch=not args.no_play and not args.check_world,
                                  progress=lambda message: print(message, flush=True))
            print('MILESTONE ' + ('PASSED' if outcome['passed'] else 'FAILED'))
            print('Return:', outcome['bundle'])
            return 0 if outcome['passed'] else 1
        gui(hub, args.ui_smoke_test)
        return 0
    except Exception as error:
        bundle = Session('launcher-error').finish(error)
        print(f'GonkSkate could not start: {error}\nReturn: {bundle}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
