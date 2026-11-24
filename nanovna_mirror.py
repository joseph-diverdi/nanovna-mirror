#!/usr/bin/env python3
# ------------------------------
"""
nanovna_mirror.py   v20261119.1

Live mirror of a NanoVNA LCD over USB (macOS, Windows, Linux).

Works with NanoVNA / NanoVNA-H (320x240) and NanoVNA-H4 (480x320) running
edy555, hugen79 or DiSlord firmware: anything that implements the shell
"capture" command (raw RGB565 framebuffer dump). The screen size is detected
automatically from the length of the first capture.
Frames are requested every 2 s by default (--period). A 480x320 capture
takes about 0.45 s, so the NanoVNA stays free about 77% of the time and its
own touch screen stays responsive.
The firmware reads pixels back from the LCD while its UI may be drawing, so a
frame taken during a redraw (e.g. moving a marker) can be scrambled; the
next frame is clean.
Not for NanoVNA-V2 / S-A-A-2 / LiteVNA, which use a different binary protocol.

Requirements:  Python 3.8+, pyserial, numpy, tkinter (Tk 8.6 for PNG save)
    pip install pyserial numpy

Usage:
    python3 nanovna_mirror.py                 # auto-find the NanoVNA
    python3 nanovna_mirror.py -p COM5         # Windows, explicit port
    python3 nanovna_mirror.py -p /dev/cu.usbmodem4001 -s 3
    python3 nanovna_mirror.py --period 1      # one frame per second

Keys in the window:
    space  pause / resume        s  save screenshot (PNG)
    + / -  change zoom           q  or Esc  quit

Written by Claude (Anthropic) in collaboration with jadv.
Reviewed, validated, and approved by jadv 2026-11-24
"""
# ------------------------------
import argparse
import queue
import sys
import threading
import time
from datetime import datetime

import numpy as np
import serial
from serial.tools import list_ports
import tkinter as tk
from tkinter import filedialog, messagebox
# ------------------------------
__version__ = "v20261119.1"

USB_VID, USB_PID = 0x0483, 0x5740        # STM32 virtual COM port (NanoVNA)
PROMPT = b"ch> "
SMALL = (320, 240)                       # NanoVNA, NanoVNA-H
LARGE = (480, 320)                       # NanoVNA-H4
# ------------------------------
def find_port():
    """Return the first serial port that looks like a NanoVNA, or None."""
    for p in list_ports.comports():
        if p.vid == USB_VID and p.pid == USB_PID:
            return p.device
    return None
# ------------------------------
class NanoVNA:
    def __init__(self, port, size=None, timeout=3.0):
        self.ser = serial.Serial(port, 115200, timeout=timeout)
        self.size = size
        self.lock = threading.Lock()
        self._sync()

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

    def _sync(self):
        """Get the shell to a known state (fresh prompt, empty buffer)."""
        self.ser.reset_input_buffer()
        self.ser.write(b"\r")
        self.ser.read_until(PROMPT)
        time.sleep(0.05)
        self.ser.reset_input_buffer()

    def _read_exact(self, n):
        buf = bytearray()
        while len(buf) < n:
            chunk = self.ser.read(n - len(buf))
            if not chunk:
                raise IOError(f"timeout: got {len(buf)} of {n} bytes")
            buf += chunk
        return bytes(buf)

    def capture(self):
        """Return one frame as an (h, w, 3) uint8 RGB array."""
        with self.lock:
            self.ser.write(b"capture\r")
            echo = self.ser.read_until(b"capture\r\n")
            if not echo.endswith(b"capture\r\n"):
                self._sync()
                raise IOError("no response to 'capture' (unsupported firmware?)")

            n_small = SMALL[0] * SMALL[1] * 2
            data = self._read_exact(n_small)
            if self.size is None:
                # Small screen: prompt follows immediately. Large: more pixels.
                tail = self._read_exact(4)
                if tail == PROMPT:
                    self.size = SMALL
                    return self._decode(data)
                n_large = LARGE[0] * LARGE[1] * 2
                data += tail + self._read_exact(n_large - n_small - 4)
                self.size = LARGE
            else:
                w, h = self.size
                data += self._read_exact(w * h * 2 - n_small)
            self.ser.read_until(PROMPT)
            return self._decode(data)

    def _decode(self, data):
        w, h = self.size
        px = np.frombuffer(data, dtype=">u2").reshape(h, w)   # big-endian RGB565
        r = (px >> 11) & 0x1F
        g = (px >> 5) & 0x3F
        b = px & 0x1F
        rgb = np.empty((h, w, 3), np.uint8)
        rgb[..., 0] = (r << 3) | (r >> 2)
        rgb[..., 1] = (g << 2) | (g >> 4)
        rgb[..., 2] = (b << 3) | (b >> 2)
        return rgb
# ------------------------------
def to_ppm(rgb, scale=1):
    if scale > 1:
        rgb = np.repeat(np.repeat(rgb, scale, axis=0), scale, axis=1)
    h, w, _ = rgb.shape
    return b"P6 %d %d 255\n" % (w, h) + rgb.tobytes()
# ------------------------------
class MirrorApp:
    def __init__(self, vna, scale, period):
        self.vna, self.scale, self.period = vna, scale, period
        self.frames = queue.Queue(maxsize=1)
        self.paused = threading.Event()
        self.stop = threading.Event()
        self.last = None
        self.t_prev, self.fps = time.time(), 0.0

        self.root = tk.Tk()
        self.root.title(f"NanoVNA mirror  {__version__}")
        self.root.configure(bg="black")
        self.img = tk.PhotoImage(width=320 * scale, height=240 * scale)
        self.label = tk.Label(self.root, image=self.img, bd=0, bg="black")
        self.label.pack()
        self.status = tk.Label(self.root, anchor="w", fg="#bbb", bg="black", font=("TkFixedFont", 10))
        self.status.pack(fill="x")

        b = self.root.bind
        b("<space>", lambda e: self.toggle_pause())
        b("s", lambda e: self.save())
        b("+", lambda e: self.rescale(+1))
        b("=", lambda e: self.rescale(+1))
        b("-", lambda e: self.rescale(-1))
        b("q", lambda e: self.quit())
        b("<Escape>", lambda e: self.quit())
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        threading.Thread(target=self.worker, daemon=True).start()
        self.root.after(20, self.poll)

    # --- capture thread -------------------------------------------------
    def worker(self):
        while not self.stop.is_set():
            if self.paused.is_set():
                self.stop.wait(0.05)
                continue
            t0 = time.monotonic()
            try:
                frame = self.vna.capture()
            except Exception as exc:          # keep going after glitches
                self.post(("error", str(exc)))
                self.stop.wait(1.0)
                continue
            self.post(("frame", frame))
            # Throttle: one capture per period, measured start to start.
            # stop.wait() returns at once on quit, so the window closes promptly.
            self.stop.wait(max(0.0, self.period - (time.monotonic() - t0)))

    def post(self, item):
        try:
            self.frames.get_nowait()
        except queue.Empty:
            pass
        self.frames.put(item)

    # --- GUI thread -----------------------------------------------------
    def poll(self):
        try:
            kind, payload = self.frames.get_nowait()
        except queue.Empty:
            kind = None
        if kind == "frame":
            self.last = payload
            self.show()
            t = time.time()
            self.fps = 0.8 * self.fps + 0.2 / max(t - self.t_prev, 1e-3)
            self.t_prev = t
            self.update_status()
        elif kind == "error":
            self.status.configure(text=f"error: {payload}")
        if not self.stop.is_set():
            self.root.after(20, self.poll)

    def show(self):
        if self.last is None:
            return
        h, w, _ = self.last.shape
        W, H = w * self.scale, h * self.scale
        if (self.img.width(), self.img.height()) != (W, H):
            # A Tk photo keeps its declared size, so resize it to the frame
            # (grow or shrink) and clear it before loading the new pixels.
            self.img.blank()
            self.img.configure(width=W, height=H)
        self.img.configure(data=to_ppm(self.last, self.scale), format="PPM")

    def update_status(self):
        w, h = self.vna.size or SMALL
        state = "PAUSED" if self.paused.is_set() else f"{self.fps:4.1f} frame/s"
        self.status.configure(
            text=f" {self.vna.ser.port}  {w}x{h}  x{self.scale}  {state}"
                 "   [space] pause  [s] save  [+/-] zoom")

    def toggle_pause(self):
        if self.paused.is_set():
            self.paused.clear()
        else:
            self.paused.set()
        self.update_status()

    def rescale(self, d):
        self.scale = min(6, max(1, self.scale + d))
        self.show()
        self.update_status()

    def save(self):
        if self.last is None:
            return
        name = datetime.now().strftime("nanovna_%Y%m%d_%H%M%S")
        png_ok = float(self.root.tk.call("info", "patchlevel")[:3]) >= 8.6
        ext = ".png" if png_ok else ".ppm"
        path = filedialog.asksaveasfilename(
            initialfile=name + ext, defaultextension=ext,
            filetypes=[("PNG", "*.png")] if png_ok else [("PPM", "*.ppm")])
        if not path:
            return
        if png_ok:
            tmp = tk.PhotoImage(data=to_ppm(self.last, 1), format="PPM")
            tmp.write(path, format="png")
        else:
            with open(path, "wb") as f:
                f.write(to_ppm(self.last, 1))
        self.status.configure(text=f" saved {path}")

    def quit(self):
        self.stop.set()
        self.root.after(100, self.root.destroy)

    def run(self):
        self.root.mainloop()
# ------------------------------
def fail(msg):
    """Report a fatal error and exit. A double-clicked app has no terminal, so also show a dialog."""
    if sys.stderr:
        print(msg, file=sys.stderr)
    if getattr(sys, "frozen", False):                  # running as a PyInstaller build
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("NanoVNA mirror", msg)
            root.destroy()
        except tk.TclError:                            # no display available
            pass
    sys.exit(1)
# ------------------------------
def main():
    ap = argparse.ArgumentParser(description="Live mirror of a NanoVNA screen.")
    ap.add_argument("-p", "--port", help="serial port (default: auto-detect)")
    ap.add_argument("-s", "--scale", type=int, default=2, help="integer zoom (default 2)")
    ap.add_argument("-r", "--period", type=float, default=2.0,
                    help="time between frame requests, s (default 2.0; 0 = as fast as possible)")
    ap.add_argument("--size", choices=["320x240", "480x320"],
                    help="force screen size instead of auto-detecting")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--version", action="version", version=__version__)
    a, _ = ap.parse_known_args()                       # ignore extra args from app launchers

    if a.list:
        for p in list_ports.comports():
            tag = "  <-- NanoVNA" if (p.vid, p.pid) == (USB_VID, USB_PID) else ""
            print(f"{p.device:28s} {p.description}{tag}")
        return

    port = a.port or find_port()
    if not port:
        fail("No NanoVNA found (USB VID 0483, PID 5740).\nPlug it in and switch it on, then start again.")
    size = tuple(int(v) for v in a.size.split("x")) if a.size else None

    try:
        vna = NanoVNA(port, size)
    except serial.SerialException as exc:
        fail(f"Cannot open {port}: {exc}\n(Close NanoVNA-Saver or NanoVNA-App first.)")
    try:
        MirrorApp(vna, max(1, a.scale), max(0.0, a.period)).run()
    finally:
        vna.close()
# ------------------------------
if __name__ == "__main__":
    main()
# ------------------------------
