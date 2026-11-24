# Changes

## v20261119.1 (approved by jadv 2026-11-24)
- Errors at startup (no NanoVNA found, port busy) now appear in a dialog
  when running as a built app, which has no terminal to print to.
- Extra command-line arguments added by app launchers are ignored.

## v20261117.4 (approved by jadv 2026-11-17)
- Default time between frames is 2 s (was 1 s).
- Docstring explains the occasional scrambled frame.

## v20261117.3
- Fixed: at startup only part of an H4 screen was shown, and zooming out
  left old pixels behind. The image now resizes to the frame.

## v20261117.2
- Removed the experimental touch feature.
- Frames requested once per period (`-r/--period`, default 1 s) instead of
  continuously, so the NanoVNA's touch screen stays responsive.

## v20261117.1
- First version.
