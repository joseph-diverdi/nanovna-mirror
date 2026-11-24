# NanoVNA mirror

A live copy of a NanoVNA's screen in a window on your computer, over USB.
Runs on macOS, Windows and Linux.

It uses the firmware's `capture` command, which sends the screen as raw
RGB565 pixels. The screen size is detected automatically:

| Model | Screen | Bytes per capture |
|---|---|---|
| NanoVNA, NanoVNA-H | 320×240 | 153,600 |
| NanoVNA-H4 | 480×320 | 307,200 |

Tested with a SeeSii NanoVNA-H4 on macOS. It should work with any NanoVNA
running edy555, hugen79 or DiSlord firmware. It does **not** work with the
NanoVNA-V2, SAA-2 or LiteVNA, which use a different binary protocol.

## Running the ready-made programs

Download the build for your system, if one is provided, and run it:

- **macOS:** unzip and open `NanoVNA Mirror.app`. The app isn't signed by
  Apple, so the first time macOS will refuse to open it. Click **Done** in
  that message, then open **System Settings → Privacy & Security**, scroll
  down to the note about "NanoVNA Mirror" being blocked, and click
  **Open Anyway**. After that it opens normally. (On macOS 14 and earlier,
  right-clicking the app and choosing **Open** also works.) A build
  only runs on Macs with the same processor type it was built on
  (Apple silicon `arm64` or Intel `x86_64`); the zip's name says which.
- **Windows:** run `NanoVNA-Mirror.exe`. Windows SmartScreen may warn about
  an unrecognized app: choose **More info**, then **Run anyway**.
- **Linux:** run `chmod +x nanovna-mirror-linux-x86_64`, then
  `./nanovna-mirror-linux-x86_64` (see the Linux notes below).

Plug in the NanoVNA and switch it on before starting the program.

## Running from source

Needs Python 3.8 or later with Tk.

    pip install -r requirements.txt
    python3 nanovna_mirror.py

Options:

| Option | Meaning |
|---|---|
| `-p PORT` | serial port, if auto-detection fails (`--list` shows the ports) |
| `-s N` | zoom factor, 1 to 6 (default 2) |
| `-r S` | time between frames, s (default 2; 0 = as fast as possible) |
| `--size 480x320` | force the screen size instead of detecting it |
| `--list` | list the serial ports and exit |

Keys in the window: **space** pause and resume, **s** save a PNG screenshot,
**+ / -** zoom, **q** or **Esc** quit.

## Behavior to expect

- **Update rate.** A 480×320 capture takes about 0.45 s (measured on an H4:
  689 kB/s), so the fastest possible rate is about 2.2 frames/s. While a
  capture is being sent, the NanoVNA responds poorly to its own touch
  screen. The 2 s default keeps it free about 77% of the time, which in
  testing left the touch screen responsive.
- **Occasional scrambled frame.** The firmware reads the pixels back out of
  the display while its own user interface may be drawing. A frame taken
  while you move a marker can come out scrambled; the next frame is clean.
- **One program at a time.** Close NanoVNA-Saver or NanoVNA-App first; only
  one program can use the serial port.

## Platform notes

- **macOS:** no driver needed; the device appears as `/dev/cu.usbmodem…`.
  Python from python.org or conda includes Tk; with Homebrew's Python also
  run `brew install python-tk`.
- **Windows 10/11:** no driver needed; the device appears as a COM port.
- **Linux:** the device appears as `/dev/ttyACM0`. Add yourself to the
  `dialout` group (`uucp` on Arch) and log in again. Install Tk with
  `sudo apt install python3-tk` (`python3-tkinter` on Fedora). If the first
  capture times out right after plugging in, ModemManager may be probing
  the port; wait a few seconds and try again.

## Building the executables

PyInstaller bundles Python and the program into a single app. Each system's
version has to be built on that system:

- macOS: `./build_macos.sh` → `dist/NanoVNA Mirror.app` and a zip of it
- Windows: `build_windows.bat` → `dist\NanoVNA-Mirror.exe`
- Linux: `./build_linux.sh` → `dist/nanovna-mirror`

On GitHub, `.github/workflows/build.yml` builds all three on GitHub's own
machines whenever a version tag (for example `v20261119.1`) is pushed, and
publishes them as a Release on the repository's **Releases** page. The
macOS build is for Apple silicon. The Linux file loses its "executable"
mark on the way; after downloading, run `chmod +x nanovna-mirror-linux-x86_64`.

## License

MIT; see `LICENSE`.

## Credits

Written by Claude (Anthropic) in collaboration with jadv.
