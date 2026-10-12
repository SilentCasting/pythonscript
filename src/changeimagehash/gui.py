"""Desktop app: drop images in, get copies with a brand-new MD5 out."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Iterable, Sequence
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from changeimagehash import __version__
from changeimagehash.core import IMAGE_EXTENSIONS, Result, change_hash, collect_files
from changeimagehash.formats import FormatError

try:  # Drag & drop is optional: the app still works without tkinterdnd2.
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

ASSETS = Path(__file__).parent / "assets"

# Table colours for each appearance mode: (background, text, selection, heading).
TABLE_COLORS = {
    "Light": ("#ffffff", "#1f2328", "#cfe3ff", "#eef1f5"),
    "Dark": ("#24272b", "#e6e6e6", "#1f538d", "#2f3338"),
}
STATUS_PENDING, STATUS_DONE, STATUS_ERROR = "Pending", "Done", "Error"

# Mixing in DnDWrapper gives the CTk window the drop_target_register() API.
_BASES = (ctk.CTk, TkinterDnD.DnDWrapper) if TkinterDnD else (ctk.CTk,)


class App(*_BASES):
    def __init__(self, initial_paths: Sequence[str] = ()) -> None:
        super().__init__()
        self.title("Change Image Hash")
        self.geometry("980x620")
        self.minsize(760, 480)
        self._set_icon()

        self.dnd_enabled = self._init_dnd()
        self.paths: dict[str, Path] = {}  # table row id -> file
        self.results: dict[str, Result] = {}  # table row id -> finished result
        self.events: queue.Queue[tuple[str, str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.save_mode = tk.StringVar(value="Save a copy")
        self.recursive = tk.BooleanVar(value=True)
        self.all_files = tk.BooleanVar(value=False)

        self._build_header()
        self._build_drop_zone()
        self._build_options()
        # The footer is packed before the table so the table shrinks first
        # when the window gets small, instead of pushing the footer away.
        self._build_footer()
        self._build_table()
        self._style_table()

        if initial_paths:
            self.add_paths(initial_paths)

    # ----------------------------------------------------------------- setup

    def _set_icon(self) -> None:
        icon = ASSETS / "icon.ico"
        if sys.platform == "win32" and icon.exists():
            # CustomTkinter sets its own icon ~200 ms after start; ours must come later.
            self.after(300, lambda: self.iconbitmap(str(icon)))

    def _init_dnd(self) -> bool:
        """Load the tkdnd Tcl extension; return False if it is unavailable."""
        if TkinterDnD is None:
            return False
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except (RuntimeError, tk.TclError):
            return False
        return True

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 8))

        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text="Change Image Hash", font=ctk.CTkFont(size=22, weight="bold")).pack(
            anchor="w"
        )
        ctk.CTkLabel(
            titles,
            text="New MD5 and SHA-256 for your images. The pictures stay exactly the same.",
            text_color=("gray35", "gray65"),
        ).pack(anchor="w")

        theme = ctk.CTkOptionMenu(
            header, values=["System", "Light", "Dark"], width=110, command=self._change_theme
        )
        theme.set("System")
        theme.pack(side="right")

    def _build_drop_zone(self) -> None:
        zone = ctk.CTkFrame(self, border_width=2, border_color=("gray75", "gray30"), corner_radius=12)
        zone.pack(fill="x", padx=20, pady=8)

        hint = "Drop images or folders here" if self.dnd_enabled else "Add images or folders"
        ctk.CTkLabel(zone, text=hint, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 2))
        formats = ", ".join(sorted(ext.lstrip(".").upper() for ext in IMAGE_EXTENSIONS))
        ctk.CTkLabel(zone, text=formats, text_color=("gray40", "gray60")).pack()

        buttons = ctk.CTkFrame(zone, fg_color="transparent")
        buttons.pack(pady=(10, 16))
        ctk.CTkButton(buttons, text="Add files…", width=130, command=self._pick_files).pack(
            side="left", padx=6
        )
        ctk.CTkButton(buttons, text="Add folder…", width=130, command=self._pick_folder).pack(
            side="left", padx=6
        )

        if self.dnd_enabled:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)

    def _build_options(self) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkSegmentedButton(
            row, values=["Save a copy", "Overwrite original"], variable=self.save_mode
        ).pack(side="left")
        ctk.CTkCheckBox(row, text="Include subfolders", variable=self.recursive).pack(
            side="left", padx=(20, 0)
        )
        ctk.CTkCheckBox(row, text="All file types", variable=self.all_files).pack(side="left", padx=(16, 0))

    def _build_table(self) -> None:
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.pack(fill="both", expand=True, padx=20, pady=4)

        columns = ("file", "status", "old", "new")
        self.table = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
        for column, title, width, stretch in (
            ("file", "File", 260, True),
            ("status", "Status", 80, False),
            ("old", "MD5 before", 260, False),
            ("new", "MD5 after", 260, False),
        ):
            self.table.heading(column, text=title, anchor="w")
            self.table.column(column, width=width, minwidth=60, stretch=stretch, anchor="w")
        self.table.tag_configure(STATUS_ERROR, foreground="#e5534b")

        scrollbar = ctk.CTkScrollbar(frame, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar.pack(side="right", fill="y", padx=4, pady=8)

        self.menu = tk.Menu(self, tearoff=False)
        self.menu.add_command(label="Copy new MD5", command=lambda: self._copy("new_md5"))
        self.menu.add_command(label="Copy new SHA-256", command=lambda: self._copy("new_sha256"))
        self.menu.add_command(label="Copy old MD5", command=lambda: self._copy("old_md5"))
        self.menu.add_separator()
        self.menu.add_command(label="Show in folder", command=self._show_in_folder)
        self.menu.add_command(label="Remove from list", command=self._remove_selected)
        self.table.bind("<Button-3>", self._open_menu)
        self.table.bind("<Double-1>", lambda _e: self._copy("new_md5"))
        self.table.bind("<Delete>", lambda _e: self._remove_selected())

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=20, pady=(8, 16))

        self.progress = ctk.CTkProgressBar(footer, width=200)
        self.progress.set(0)
        self.progress.pack(side="left")
        self.status = ctk.CTkLabel(footer, text=self._idle_text(), text_color=("gray35", "gray65"))
        self.status.pack(side="left", padx=12)

        self.start_button = ctk.CTkButton(
            footer, text="Change hashes", width=150, font=ctk.CTkFont(weight="bold"), command=self.start
        )
        self.start_button.pack(side="right")
        self.clear_button = ctk.CTkButton(
            footer,
            text="Clear list",
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self.clear,
        )
        self.clear_button.pack(side="right", padx=8)

    # ---------------------------------------------------------------- theming

    def _change_theme(self, mode: str) -> None:
        ctk.set_appearance_mode(mode)
        self._style_table()

    def _style_table(self) -> None:
        """ttk widgets ignore CustomTkinter themes, so colour the table by hand."""
        background, text, selected, heading = TABLE_COLORS[ctk.get_appearance_mode()]
        scaling = ctk.ScalingTracker.get_window_scaling(self)
        style = ttk.Style(self)
        style.theme_use("clam")
        # Drop the default 1px frame around the rows; the CTkFrame is the border.
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.configure(
            "Treeview",
            background=background,
            fieldbackground=background,
            foreground=text,
            rowheight=int(28 * scaling),
            borderwidth=0,
            font=("Consolas", 10),
        )
        style.map("Treeview", background=[("selected", selected)], foreground=[("selected", text)])
        style.configure(
            "Treeview.Heading",
            background=heading,
            foreground=text,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview.Heading", background=[("active", heading)])

    # ------------------------------------------------------------ adding files

    def _pick_files(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in sorted(IMAGE_EXTENSIONS))
        chosen = filedialog.askopenfilenames(
            parent=self, title="Choose images", filetypes=[("Images", patterns), ("All files", "*.*")]
        )
        self.add_paths(chosen)

    def _pick_folder(self) -> None:
        folder = filedialog.askdirectory(parent=self, title="Choose a folder")
        if folder:
            self.add_paths([folder])

    def _on_drop(self, event: tk.Event) -> None:
        # Paths with spaces arrive wrapped in {braces}; splitlist unwraps them.
        self.add_paths(self.tk.splitlist(event.data))

    def add_paths(self, raw_paths: Iterable[str]) -> None:
        files = collect_files(raw_paths, recursive=self.recursive.get(), all_files=self.all_files.get())
        known = {path.resolve() for path in self.paths.values()}
        added = 0
        for path in files:
            if path.resolve() in known:
                continue
            row = self.table.insert("", "end", values=(path.name, STATUS_PENDING, "", ""))
            self.paths[row] = path
            added += 1
        self._set_status(f"Added {added} file(s). " + self._idle_text())

    # -------------------------------------------------------------- processing

    def start(self) -> None:
        pending = [row for row in self.paths if row not in self.results]
        if not pending:
            self._set_status("Nothing to do: add some images first.")
            return
        overwrite = self.save_mode.get() == "Overwrite original"
        if overwrite and not messagebox.askyesno(
            "Overwrite originals?",
            f"{len(pending)} original file(s) will be modified in place. Continue?",
            parent=self,
        ):
            return

        self._set_busy(True)
        self.progress.set(0)
        jobs = [(row, self.paths[row]) for row in pending]
        self.worker = threading.Thread(target=self._work, args=(jobs, overwrite), daemon=True)
        self.worker.start()
        self.after(50, self._poll, len(jobs), 0)

    def _work(self, jobs: list[tuple[str, Path]], overwrite: bool) -> None:
        """Runs in a background thread so the window never freezes."""
        for row, path in jobs:
            try:
                self.events.put(("done", row, change_hash(path, overwrite=overwrite)))
            except (OSError, FormatError) as exc:
                self.events.put(("error", row, str(exc)))

    def _poll(self, total: int, finished: int) -> None:
        """Apply results from the worker thread; Tk may only be touched here."""
        while True:
            try:
                kind, row, value = self.events.get_nowait()
            except queue.Empty:
                break
            finished += 1
            name = self.paths[row].name
            if kind == "done":
                self.results[row] = value
                self.table.item(
                    row, values=(value.output.name, STATUS_DONE, value.before.md5, value.after.md5)
                )
            else:
                self.table.item(row, values=(name, STATUS_ERROR, value, ""), tags=(STATUS_ERROR,))
            self.progress.set(finished / total)
            self._set_status(f"Processing {finished}/{total}…")

        if finished < total:
            self.after(50, self._poll, total, finished)
        else:
            self._set_busy(False)
            self._set_status(f"Finished {total} file(s). Double-click a row to copy its new MD5.")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.start_button.configure(state=state)
        self.clear_button.configure(state=state)

    # ------------------------------------------------------------ row actions

    def _open_menu(self, event: tk.Event) -> None:
        row = self.table.identify_row(event.y)
        if row:
            if row not in self.table.selection():
                self.table.selection_set(row)
            self.menu.tk_popup(event.x_root, event.y_root)

    def _copy(self, field: str) -> None:
        values = []
        for row in self.table.selection():
            result = self.results.get(row)
            if result:
                values.append(
                    {
                        "new_md5": result.after.md5,
                        "new_sha256": result.after.sha256,
                        "old_md5": result.before.md5,
                    }[field]
                )
        if values:
            self.clipboard_clear()
            self.clipboard_append("\n".join(values))
            self._set_status(f"Copied {len(values)} hash(es) to the clipboard.")

    def _show_in_folder(self) -> None:
        selection = self.table.selection()
        if not selection:
            return
        row = selection[0]
        path = self.results[row].output if row in self.results else self.paths[row]
        if sys.platform == "win32":
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path.parent)], check=False)

    def _remove_selected(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        for row in self.table.selection():
            self.table.delete(row)
            self.paths.pop(row, None)
            self.results.pop(row, None)
        self._set_status(self._idle_text())

    def clear(self) -> None:
        self.table.delete(*self.table.get_children())
        self.paths.clear()
        self.results.clear()
        self.progress.set(0)
        self._set_status(self._idle_text())

    def _idle_text(self) -> str:
        count = len(getattr(self, "paths", {}))
        return f"{count} file(s) in the list · v{__version__}"

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)


def main(argv: Sequence[str] | None = None) -> None:
    """Start the app; any paths passed in (e.g. dropped onto the .exe) are preloaded."""
    if sys.platform == "win32":
        # Show our own icon in the taskbar instead of the generic Python one.
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SilentCasting.ChangeImageHash")
        except (AttributeError, OSError):
            pass
    ctk.set_appearance_mode("System")
    paths = sys.argv[1:] if argv is None else argv
    App(initial_paths=[p for p in paths if os.path.exists(p)]).mainloop()


if __name__ == "__main__":
    main()
