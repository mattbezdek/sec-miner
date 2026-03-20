from __future__ import annotations

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

        ttk.Checkbutton(frame, text="Include JSON manifest", variable=self.include_manifest).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=2
        )
        ttk.Checkbutton(frame, text="Write combined markdown file", variable=self.combined_file).grid(
            row=6, column=2, columnspan=2, sticky="w", pady=2
        )

        ttk.Button(frame, text="Run", command=self._run).grid(row=7, column=0, pady=8, sticky="w")

        ttk.Label(frame, text="Progress / Summary:").grid(row=8, column=0, sticky="w")
        self.log_box = tk.Text(frame, width=90, height=10)
        self.log_box.grid(row=9, column=0, columnspan=4, sticky="nsew", pady=4)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(9, weight=1)

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
        except queue.Empty:
            pass
        self.root.after(100, self._schedule_log_drain)

    def _build_config(self):
        targets = [line.strip() for line in self.targets_box.get("1.0", tk.END).splitlines() if line.strip()]
        if not targets:
            raise ValueError("Please provide at least one target (CIK, ticker, or company name).")
        rate = float(self.rate_limit.get().strip() or "2.0")
        return load_config(
            identity=self.identity.get().strip(),
            api_token=self.api_token.get().strip() or None,
            targets=targets,
            output_dir=self.output_dir.get().strip(),
            include_manifest=self.include_manifest.get(),
            combined_file=self.combined_file.get(),
            rate_limit_rps=rate,
        )

    def _run(self) -> None:
        self.log_box.delete("1.0", tk.END)
        self._queue_log("Starting run...")

        try:
            config = self._build_config()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Configuration error", str(exc))
            return

        def worker() -> None:
            try:
                summary = run_pipeline(config, logger=self._queue_log)
                self._queue_log(f"Done. Success: {summary.success_count}, Failed: {summary.failure_count}")
            except Exception as exc:  # noqa: BLE001
                self._queue_log(f"Unexpected failure: {exc}")

        threading.Thread(target=worker, daemon=True).start()


def launch() -> None:
    root = tk.Tk()
    Sec10KApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
