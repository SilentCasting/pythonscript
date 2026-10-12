# Changelog

## [1.0.0] - 2026-10-12

Complete rewrite of the original 2022 script into a full app.

### Added
- Desktop app built with CustomTkinter: light/dark theme, drag & drop,
  batch processing of files and folders, MD5 before/after table, copy hashes
  to the clipboard, "Show in folder".
- Command line tool `changeimagehash` with `--overwrite`, `--output-dir`,
  `--recursive`, `--all-files` and `--json`.
- Format-aware changes that keep files valid: PNG text chunk, JPEG comment,
  GIF comment. WEBP, BMP, TIFF and other files get bytes appended.
- Support for PNG, JPG/JPEG/JFIF, GIF, WEBP, BMP and TIFF (and any file with
  "All file types").
- Tests, CI on Windows and Linux, and a ready-to-run `.exe` on every release.

### Changed
- The original file is now left untouched by default; a `_unique` copy is
  saved next to it. Overwriting is opt-in.

## [0.1.0] - 2022-02-21

- First version: a tkinter button that appended random digits to a PNG/GIF.
