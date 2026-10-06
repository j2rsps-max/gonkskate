"""Select local THUG character sources without constructing command-line paths."""
from pathlib import Path

FIELDS = (
    ("skeleton", "Skeleton (required)", "*.ske*"),
    ("skin", "Matching mesh (required)", "*.skin*"),
    ("textures", "Textures (optional)", "*.tex*"),
    ("animation", "Animation (optional)", "*.ska*"),
    ("q_table", "Q48 table (if required by clip)", "*"),
    ("t_table", "T48 table (if required by clip)", "*"),
)
PROFILES = {"THUG PC / DX9": "dx9", "Original Xbox": "xbox"}


def validate_sources(selection):
    """Validate existence before a decoder opens any file; preserve source paths."""
    result = {}
    for name, label, _ in FIELDS:
        value = selection.get(name)
        if value is None or not str(value).strip():
            if name in ("skeleton", "skin"):
                raise ValueError("Select the original THUG skeleton and its matching mesh.")
            result[name] = None
            continue
        path = Path(str(value).strip().strip('"'))
        if not path.is_file():
            raise ValueError(label.split(" (")[0] + " file was not found: " + str(path) +
                             "\nC:\\path\\... is an example, not an installed game location. "
                             "Use RUN_CHARACTER_IMPORT.cmd to browse for your actual THUG files.")
        result[name] = path
    profile = selection.get("weight_profile")
    if profile not in PROFILES.values():
        raise ValueError("Select the files' original platform: THUG PC / DX9 or Original Xbox.")
    if result["animation"] is None and (result["q_table"] is not None or result["t_table"] is not None):
        raise ValueError("Compression tables require a matching animation clip.")
    result["weight_profile"] = profile
    return result


class CharacterFilePicker:
    def __init__(self):
        # Lazy import: the asset-free console check does not require Tk.
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
        self.filedialog, self.messagebox = filedialog, messagebox
        self.root = tk.Tk()
        self.root.title("GonkSkate — Import THUG character")
        self.root.minsize(700, 360)
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)
        self.result = None
        self.values = {name: tk.StringVar(self.root) for name, _, _ in FIELDS}
        self.profile = tk.StringVar(self.root, "Select original platform")
        panel = ttk.Frame(self.root, padding=16)
        panel.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)
        ttk.Label(panel, text="Choose matching files from your installed or extracted THUG game.").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Label(panel, text="Game files are not included in the GonkSkate download.").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))
        for row, (name, label, pattern) in enumerate(FIELDS, 2):
            ttk.Label(panel, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
            ttk.Entry(panel, textvariable=self.values[name], width=50).grid(row=row, column=1, sticky="ew", pady=4)
            ttk.Button(panel, text="Browse…", command=lambda n=name, p=pattern: self.browse(n, p)).grid(
                row=row, column=2, padx=(8, 0), pady=4)
        ttk.Label(panel, text="Original platform (required)").grid(row=8, column=0, sticky="w", pady=8)
        ttk.Combobox(panel, textvariable=self.profile, values=list(PROFILES), state="readonly").grid(
            row=8, column=1, sticky="ew", pady=8)
        ttk.Label(panel, text="Imports stay on this PC. The results ZIP contains diagnostics only.").grid(
            row=9, column=0, columnspan=3, sticky="w", pady=8)
        buttons = ttk.Frame(panel)
        buttons.grid(row=10, column=0, columnspan=3, sticky="e")
        ttk.Button(buttons, text="Cancel", command=self.cancel).pack(side="left", padx=8)
        ttk.Button(buttons, text="Import character", command=self.submit).pack(side="left")

    def browse(self, name, pattern):
        chosen = self.filedialog.askopenfilename(parent=self.root, title="Select " + name.replace("_", " "),
            filetypes=[("THUG source files", pattern), ("All files", "*")])
        if chosen:
            self.values[name].set(chosen)

    def submit(self):
        selected = {name: value.get() for name, value in self.values.items()}
        selected["weight_profile"] = PROFILES.get(self.profile.get())
        try:
            self.result = validate_sources(selected)
        except ValueError as error:
            self.messagebox.showerror("Check selected files", str(error), parent=self.root)
            return
        self.root.destroy()

    def cancel(self):
        self.result = None
        self.root.destroy()


def choose_character_files():
    try:
        import tkinter as tk
    except ImportError as error:
        raise RuntimeError("The file picker needs Python with Tcl/Tk support. "
                           "Use the standard Python Windows installer with Tcl/Tk selected, "
                           "or run RUN_CHARACTER_CHECK.cmd with actual file paths.") from error
    try:
        picker = CharacterFilePicker()
    except tk.TclError as error:
        raise RuntimeError("The file picker needs Python with Tcl/Tk support. "
                           "Use the standard Python Windows installer with Tcl/Tk selected, "
                           "or run RUN_CHARACTER_CHECK.cmd with actual file paths.") from error
    picker.root.mainloop()
    return picker.result
