from __future__ import annotations

import logging
import os
from typing import Optional

import customtkinter as ctk

from handsfree_claude import audio, config as config_mod, paths, state as state_mod

logger = logging.getLogger(__name__)

WINDOW_TITLE = "HandsFree Claude"
WINDOW_SIZE = (340, 180)
SETTINGS_SIZE = (400, 300)

COLOR_OFF = "#9ca3af"   # gray
COLOR_ON = "#22c55e"    # green

POLL_INTERVAL_MS = 400   # re-read state in case something else updated it


def run() -> None:
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    app = MainWindow()
    app.mainloop()


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self._cfg = config_mod.load()
        self._alive = True
        self._pid = os.getpid()

        self.title(WINDOW_TITLE)
        self.attributes("-topmost", True)
        x, y = self._clamp_to_screen(*self._cfg.window_position)
        self.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}+{x}+{y}")
        self.minsize(*WINDOW_SIZE)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start OFF — the window being open does not mean HandsFree is on.
        state_mod.write(enabled=False, pid=self._pid)
        self._enabled = False

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=16, pady=14)

        # Row 1: title + settings gear
        top_row = ctk.CTkFrame(outer, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(
            top_row,
            text=WINDOW_TITLE,
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            top_row,
            text="⚙",  # gear
            width=32,
            height=28,
            font=ctk.CTkFont(size=16),
            command=self._open_settings,
        ).pack(side="right")

        # Row 2: status light + label
        status_row = ctk.CTkFrame(outer, fg_color="transparent")
        status_row.pack(fill="x", pady=(16, 12))
        self._light = ctk.CTkLabel(
            status_row,
            text="",
            width=14,
            height=14,
            corner_radius=7,
            fg_color=COLOR_OFF,
        )
        self._light.pack(side="left", padx=(0, 10))
        self._status_label = ctk.CTkLabel(
            status_row,
            text="HandsFree mode: OFF",
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        self._status_label.pack(side="left", fill="x", expand=True)

        # Row 3: toggle button
        self._toggle_button = ctk.CTkButton(
            outer,
            text="Turn ON",
            height=36,
            command=self._toggle,
        )
        self._toggle_button.pack(fill="x")

        self._schedule_poll()

    def _clamp_to_screen(self, x: int, y: int) -> tuple[int, int]:
        """Keep the window origin inside the primary screen so a user who moves it
        onto a monitor that later goes away can still find it on relaunch."""
        self.update_idletasks()
        w, h = WINDOW_SIZE
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        return max(0, min(x, sw - w)), max(0, min(y, sh - h))

    def _toggle(self) -> None:
        self._enabled = not self._enabled
        state_mod.write(enabled=self._enabled, pid=self._pid)
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        if self._enabled:
            self._light.configure(fg_color=COLOR_ON)
            self._status_label.configure(text="HandsFree mode: ON")
            self._toggle_button.configure(text="Turn OFF")
        else:
            self._light.configure(fg_color=COLOR_OFF)
            self._status_label.configure(text="HandsFree mode: OFF")
            self._toggle_button.configure(text="Turn ON")

    def _schedule_poll(self) -> None:
        if not self._alive:
            return
        s = state_mod.read()
        if s.enabled != self._enabled:
            self._enabled = s.enabled
            self._refresh_ui()
        self.after(POLL_INTERVAL_MS, self._schedule_poll)

    def _open_settings(self) -> None:
        SettingsDialog(self, self._cfg, on_save=self._apply_cfg)

    def _apply_cfg(self, cfg: config_mod.Config) -> None:
        self._cfg = cfg
        config_mod.save(cfg)

    def _on_close(self) -> None:
        self._alive = False
        try:
            self._cfg.window_position = (self.winfo_x(), self.winfo_y())
            config_mod.save(self._cfg)
        except Exception as exc:
            logger.warning("failed to persist window position: %s", exc)
        state_mod.clear()
        self.destroy()


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, cfg: config_mod.Config, on_save) -> None:
        super().__init__(parent)
        self._original_cfg = cfg
        self._working_cfg = config_mod.Config(
            end_sound_file=cfg.end_sound_file,
            custom_sound_path=cfg.custom_sound_path,
            mute_sound=cfg.mute_sound,
            window_position=cfg.window_position,
        )
        self._on_save = on_save

        self.title("HandsFree Claude — Settings")
        self.attributes("-topmost", True)
        self.geometry(f"{SETTINGS_SIZE[0]}x{SETTINGS_SIZE[1]}")
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        # End sound dropdown
        self._end_sounds: list[tuple[str, str]] = audio.list_end_sounds()
        labels_to_files = {lbl: fn for fn, lbl in self._end_sounds}
        files_to_labels = {fn: lbl for fn, lbl in self._end_sounds}
        default_label = files_to_labels.get(cfg.end_sound_file, "Default")
        self._labels_to_files = labels_to_files

        ctk.CTkLabel(frame, text="End sound:", anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self._end_sound_var = ctk.StringVar(value=default_label)
        self._end_sound_menu = ctk.CTkOptionMenu(
            frame,
            values=[lbl for _, lbl in self._end_sounds] or ["Default"],
            variable=self._end_sound_var,
            width=180,
        )
        self._end_sound_menu.grid(row=1, column=0, sticky="w", pady=(0, 4))
        ctk.CTkButton(
            frame, text="▶ Preview", width=90, command=self._preview
        ).grid(row=1, column=1, sticky="e", padx=(8, 0), pady=(0, 4))

        # Custom sound
        ctk.CTkLabel(frame, text="Custom sound file:", anchor="w").grid(
            row=2, column=0, sticky="w", pady=(12, 4)
        )
        self._custom_var = ctk.StringVar(value=cfg.custom_sound_path or "")
        self._custom_entry = ctk.CTkEntry(frame, textvariable=self._custom_var)
        self._custom_entry.grid(row=3, column=0, sticky="ew", pady=(0, 4))
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=3, column=1, sticky="e", padx=(8, 0), pady=(0, 4))
        ctk.CTkButton(
            btn_row, text="Browse…", width=80, command=self._browse
        ).pack(side="left")
        ctk.CTkButton(
            btn_row, text="Clear", width=60, command=self._clear_custom
        ).pack(side="left", padx=(4, 0))

        # Mute
        self._mute_var = ctk.BooleanVar(value=cfg.mute_sound)
        ctk.CTkCheckBox(
            frame, text="Mute sound", variable=self._mute_var
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(16, 0))

        # Save/Cancel
        button_row = ctk.CTkFrame(frame, fg_color="transparent")
        button_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(24, 0))
        button_row.columnconfigure(0, weight=1)
        ctk.CTkButton(
            button_row, text="Cancel", width=80, command=self._on_cancel
        ).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(
            button_row, text="Save", width=80, command=self._on_save_clicked
        ).grid(row=0, column=2)

        frame.columnconfigure(0, weight=1)

    def _browse(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose end sound",
            filetypes=[("Audio files", "*.mp3 *.wav"), ("All files", "*.*")],
        )
        if path:
            self._custom_var.set(path)

    def _clear_custom(self) -> None:
        self._custom_var.set("")

    def _preview(self) -> None:
        cfg = self._build_working_cfg()
        p = audio.effective_sound_path(cfg)
        if p is None:
            return
        audio.play_end_sound_preview(p)

    def _build_working_cfg(self) -> config_mod.Config:
        filename = self._labels_to_files.get(
            self._end_sound_var.get(), self._working_cfg.end_sound_file
        )
        return config_mod.Config(
            end_sound_file=filename,
            custom_sound_path=self._custom_var.get().strip() or None,
            mute_sound=bool(self._mute_var.get()),
            window_position=self._working_cfg.window_position,
        )

    def _on_save_clicked(self) -> None:
        audio.stop_end_sound_preview()
        self._on_save(self._build_working_cfg())
        self.destroy()

    def _on_cancel(self) -> None:
        audio.stop_end_sound_preview()
        self.destroy()
