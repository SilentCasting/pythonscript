"""Core logic shared by the desktop app and the command line tool."""

from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from changeimagehash.formats import inject

# Extensions picked up when scanning folders (unless "all files" is enabled).
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".jfif", ".gif", ".webp", ".bmp", ".tif", ".tiff"})

# Added to the file name when saving a copy: photo.png -> photo_unique.png
DEFAULT_SUFFIX = "_unique"


@dataclass(frozen=True)
class Hashes:
    """MD5 and SHA-256 digests of a file's contents, as hex strings."""

    md5: str
    sha256: str

    @classmethod
    def of(cls, data: bytes) -> Hashes:
        return cls(hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest())


@dataclass(frozen=True)
class Result:
    """Outcome of changing the hash of one file."""

    source: Path
    output: Path
    method: str
    before: Hashes
    after: Hashes


def make_payload() -> bytes:
    """Return 32 random hex characters; enough to make every hash unique."""
    return secrets.token_hex(16).encode("ascii")


def output_path_for(source: Path, suffix: str = DEFAULT_SUFFIX, output_dir: Path | None = None) -> Path:
    """Pick a free path for the copy, adding _2, _3, ... if the name is taken."""
    folder = output_dir or source.parent
    candidate = folder / f"{source.stem}{suffix}{source.suffix}"
    counter = 2
    while candidate.exists():
        candidate = folder / f"{source.stem}{suffix}_{counter}{source.suffix}"
        counter += 1
    return candidate


def _write_atomic(target: Path, data: bytes, mode_from: Path) -> None:
    """Write via a temp file and rename, so a crash never leaves half a file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(data)
        shutil.copymode(mode_from, tmp_name)
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def change_hash(
    source: str | os.PathLike[str],
    *,
    overwrite: bool = False,
    suffix: str = DEFAULT_SUFFIX,
    output_dir: str | os.PathLike[str] | None = None,
) -> Result:
    """Give ``source`` a new MD5/SHA-256 hash without changing how it looks.

    By default the original is left untouched and a copy is written next to
    it (or into ``output_dir``). With ``overwrite=True`` the original file is
    replaced instead.
    """
    source = Path(source)
    data = source.read_bytes()
    new_data, method = inject(data, make_payload())

    if overwrite:
        target = source
    else:
        target = output_path_for(source, suffix, Path(output_dir) if output_dir else None)
    _write_atomic(target, new_data, mode_from=source)

    return Result(source, target, method, Hashes.of(data), Hashes.of(new_data))


def collect_files(
    paths: Iterable[str | os.PathLike[str]],
    *,
    recursive: bool = False,
    all_files: bool = False,
) -> list[Path]:
    """Expand files and folders into a de-duplicated list of files.

    The order of ``paths`` is kept; the contents of each folder are sorted.

    Files given explicitly are always included. Files found inside folders
    are included only if they have an image extension, unless ``all_files``.
    """
    found: dict[Path, None] = {}  # dict keeps insertion order and drops duplicates
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            entries = path.rglob("*") if recursive else path.iterdir()
            matches = (
                p for p in entries if p.is_file() and (all_files or p.suffix.lower() in IMAGE_EXTENSIONS)
            )
            for match in sorted(matches):
                found[match] = None
        elif path.is_file():
            found[path] = None
    return list(found)
