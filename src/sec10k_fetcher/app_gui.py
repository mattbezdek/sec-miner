from __future__ import annotations

import json
import os
import platform
import subprocess
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from sec10k_fetcher.config import load_config
from sec10k_fetcher.pipeline import run_pipeline


class Sec10KApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SEC-miner")
        self.root.geometry("900x700")

        self.identity = tk.StringVar()
        self.api_token = tk.StringVar()
        self.output_dir = tk.StringVar(value="output")
        self.rate_limit = tk.StringVar(value="2.0")
        self.include_manifest = tk.BooleanVar(value=False)
        self.combined_file = tk.BooleanVar(value=True)
        self.max_workers = tk.StringVar(value="1")
        self.report_format = tk.StringVar(value="none")
        self.progress = tk.DoubleVar(value=0.0)
        self.progress_label = tk.StringVar(value="0 / 0")
        self._cancel_event = threading.Event()
        self._running = False
        self._total_targets = 0
        self._completed_targets = 0

        self.log_box: tk.Text
        self.targets_box: tk.Text
        self._log_queue: queue.Queue[str] = queue.Queue()

        self._build_layout()
        self._schedule_log_drain()

    def _build_layout(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="SEC Identity (required):").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.identity, width=80).grid(
            row=0, column=1, columnspan=3, sticky="ew", padx=4, pady=4
        )
        ttk.Label(
            frame,
            text="Example: Jane Doe jane.doe@example.com",
        ).grid(row=1, column=1, columnspan=3, sticky="w")

        ttk.Label(frame, text="Optional API Token:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.api_token, width=80, show="*").grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=4, pady=4
        )

        ttk.Label(frame, text="Targets (one per line, CIK/ticker/name):").grid(
            row=3, column=0, sticky="nw"
        )
        self.targets_box = tk.Text(frame, width=70, height=6)
        self.targets_box.grid(row=3, column=1, columnspan=3, sticky="ew", padx=4, pady=4)

        ttk.Label(frame, text="Output Directory:").grid(row=4, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.output_dir, width=60).grid(
            row=4, column=1, sticky="ew", padx=4, pady=4
        )
        ttk.Button(frame, text="Browse", command=self._browse_output_dir).grid(row=4, column=2, sticky="w")

        ttk.Label(frame, text="Rate Limit (req/sec):").grid(row=5, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.rate_limit, width=10).grid(row=5, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(frame, text="Max Workers:").grid(row=5, column=2, sticky="e")
        ttk.Entry(frame, textvariable=self.max_workers, width=8).grid(row=5, column=3, sticky="w", padx=4, pady=4)

        ttk.Checkbutton(frame, text="Include JSON manifest", variable=self.include_manifest).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=2
        )
        ttk.Checkbutton(frame, text="Write combined markdown file", variable=self.combined_file).grid(
            row=6, column=2, columnspan=2, sticky="w", pady=2
        )

        ttk.Label(frame, text="Report format:").grid(row=7, column=0, sticky="w")
        ttk.Combobox(
            frame,
            textvariable=self.report_format,
            values=["none", "markdown", "html"],
            state="readonly",
            width=12,
        ).grid(row=7, column=1, sticky="w", padx=4, pady=4)

        ttk.Button(frame, text="Run", command=self._run).grid(row=7, column=2, pady=8, sticky="e")
        ttk.Button(frame, text="Cancel", command=self._cancel).grid(row=7, column=3, pady=8, sticky="w")
        ttk.Button(frame, text="Save Preset", command=self._save_preset).grid(row=8, column=0, pady=4, sticky="w")
        ttk.Button(frame, text="Load Preset", command=self._load_preset).grid(row=8, column=1, pady=4, sticky="w")
        ttk.Button(frame, text="Open Output Folder", command=self._open_output_folder).grid(
            row=8, column=2, columnspan=2, pady=4, sticky="w"
        )

        ttk.Label(frame, text="Progress / Summary:").grid(row=9, column=0, sticky="w")
        ttk.Progressbar(frame, variable=self.progress, maximum=100).grid(
            row=9, column=1, columnspan=2, sticky="ew", padx=4
        )
        ttk.Label(frame, textvariable=self.progress_label).grid(row=9, column=3, sticky="w")
        self.log_box = tk.Text(frame, width=90, height=10)
        self.log_box.grid(row=10, column=0, columnspan=4, sticky="nsew", pady=4)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(10, weight=1)

    def _browse_output_dir(self) -> None:
        chosen = filedialog.askdirectory()
        if chosen:
            self.output_dir.set(chosen)

    def _append_log(self, message: str) -> None:
        self.log_box.insert(tk.END, f"{message}\n")
        self.log_box.see(tk.END)

    def _queue_log(self, message: str) -> None:
        self._log_queue.put(message)

    def _schedule_log_drain(self) -> None:
        try:
            while True:
                message = self._log_queue.get_nowait()
                self._append_log(message)
                if message.startswith("Target complete:"):
                    if self._running and self._total_targets > 0:
                        self._completed_targets = min(self._completed_targets + 1, self._total_targets)
                        self._set_progress(self._completed_targets, self._total_targets)
                elif message.startswith("Done."):
                    # Ensure UI lands on 100% even if logs arrive out of order.
                    if self._total_targets > 0:
                        self._completed_targets = self._total_targets
                        self._set_progress(self._completed_targets, self._total_targets)
        except queue.Empty:
            pass
        self.root.after(100, self._schedule_log_drain)

    def _build_config(self):
        targets = [line.strip() for line in self.targets_box.get("1.0", tk.END).splitlines() if line.strip()]
        if not targets:
            raise ValueError("Please provide at least one target (CIK, ticker, or company name).")
        rate = float(self.rate_limit.get().strip() or "2.0")
        workers = int(self.max_workers.get().strip() or "1")
        return load_config(
            identity=self.identity.get().strip(),
            api_token=self.api_token.get().strip() or None,
            targets=targets,
            output_dir=self.output_dir.get().strip(),
            include_manifest=self.include_manifest.get(),
            combined_file=self.combined_file.get(),
            rate_limit_rps=rate,
            max_workers=workers,
            report_format=self.report_format.get().strip(),
        )

    def _set_progress(self, completed: int, total: int) -> None:
        if total <= 0:
            self.progress.set(0)
            self.progress_label.set("0 / 0")
            return
        self.progress.set((completed / total) * 100.0)
        self.progress_label.set(f"{completed} / {total}")

    def _save_preset(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            title="Save preset",
        )
        if not path:
            return
        payload = {
            "identity": self.identity.get(),
            "api_token": self.api_token.get(),
            "targets": self.targets_box.get("1.0", tk.END),
            "output_dir": self.output_dir.get(),
            "rate_limit": self.rate_limit.get(),
            "include_manifest": self.include_manifest.get(),
            "combined_file": self.combined_file.get(),
            "max_workers": self.max_workers.get(),
            "report_format": self.report_format.get(),
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        self._queue_log(f"Preset saved: {path}")

    def _load_preset(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], title="Load preset")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.identity.set(payload.get("identity", ""))
        self.api_token.set(payload.get("api_token", ""))
        self.targets_box.delete("1.0", tk.END)
        self.targets_box.insert("1.0", payload.get("targets", ""))
        self.output_dir.set(payload.get("output_dir", "output"))
        self.rate_limit.set(payload.get("rate_limit", "2.0"))
        self.include_manifest.set(bool(payload.get("include_manifest", False)))
        self.combined_file.set(bool(payload.get("combined_file", True)))
        self.max_workers.set(str(payload.get("max_workers", "1")))
        self.report_format.set(payload.get("report_format", "none"))
        self._queue_log(f"Preset loaded: {path}")

    def _open_output_folder(self) -> None:
        path = self.output_dir.get().strip()
        if not path:
            return
        try:
            system = platform.system().lower()
            if system == "darwin":
                subprocess.run(["open", path], check=False)
            elif system == "windows":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as exc:  # noqa: BLE001
            self._queue_log(f"Failed to open output folder: {exc}")

    def _cancel(self) -> None:
        if self._running:
            self._cancel_event.set()
            self._queue_log("Cancellation requested...")

    def _run(self) -> None:
        if self._running:
            messagebox.showinfo("Run in progress", "A run is already in progress.")
            return
        self.log_box.delete("1.0", tk.END)
        self._queue_log("Starting run...")
        self._cancel_event.clear()

        try:
            config = self._build_config()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Configuration error", str(exc))
            return
        total_targets = len(config.targets)
        self._total_targets = total_targets
        self._completed_targets = 0
        self._set_progress(self._completed_targets, self._total_targets)
        self._running = True

        def worker() -> None:
            try:
                summary = run_pipeline(config, logger=self._queue_log, cancel_event=self._cancel_event)
                self._queue_log(
                    "Done. "
                    f"Success: {summary.success_count}, Skipped: {summary.skipped_count}, "
                    f"Failed: {summary.failure_count}"
                )
                if summary.cancelled:
                    self._queue_log("Run ended after cancellation request.")
            except Exception as exc:  # noqa: BLE001
                self._queue_log(f"Unexpected failure: {exc}")
            finally:
                self._running = False

        threading.Thread(target=worker, daemon=True).start()


def launch() -> None:
    root = tk.Tk()
    Sec10KApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
