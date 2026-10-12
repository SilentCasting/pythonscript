from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from conftest import make_image
from PIL import Image, ImageChops

from changeimagehash.core import change_hash, collect_files, output_path_for
from changeimagehash.formats import (
    METHOD_APPEND,
    METHOD_GIF,
    METHOD_JPEG,
    METHOD_PNG,
    FormatError,
    inject,
)

EXPECTED_METHOD = {
    ".png": METHOD_PNG,
    ".jpg": METHOD_JPEG,
    ".gif": METHOD_GIF,
    ".webp": METHOD_APPEND,
    ".bmp": METHOD_APPEND,
    ".tiff": METHOD_APPEND,
}


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def test_copy_has_new_hash_and_same_pixels(image_file: Path) -> None:
    original_bytes = image_file.read_bytes()

    result = change_hash(image_file)

    assert result.output == image_file.with_name(f"sample_unique{image_file.suffix}")
    assert image_file.read_bytes() == original_bytes, "original must stay untouched"
    assert result.before.md5 == md5(image_file)
    assert result.after.md5 == md5(result.output)
    assert result.after.md5 != result.before.md5
    assert result.after.sha256 != result.before.sha256
    assert result.method == EXPECTED_METHOD[image_file.suffix]

    with Image.open(image_file) as before, Image.open(result.output) as after:
        after.load()  # fully decode: a broken file would raise here
        assert ImageChops.difference(before.convert("RGB"), after.convert("RGB")).getbbox() is None


def test_overwrite_modifies_original(image_file: Path) -> None:
    old = md5(image_file)

    result = change_hash(image_file, overwrite=True)

    assert result.output == image_file
    assert md5(image_file) == result.after.md5 != old
    assert list(image_file.parent.iterdir()) == [image_file], "no temp files left behind"


def test_every_run_gives_a_different_hash(tmp_path: Path) -> None:
    image = make_image(tmp_path / "a.png")
    hashes = {change_hash(image).after.md5 for _ in range(5)}
    assert len(hashes) == 5


def test_output_dir_and_name_collisions(tmp_path: Path) -> None:
    image = make_image(tmp_path / "a.png")
    out = tmp_path / "out"

    first = change_hash(image, output_dir=out, suffix="-x")
    second = change_hash(image, output_dir=out, suffix="-x")

    assert first.output == out / "a-x.png"
    assert second.output == out / "a-x_2.png"
    assert output_path_for(image, "-x", out) == out / "a-x_3.png"


def test_collect_files(tmp_path: Path) -> None:
    make_image(tmp_path / "b.png")
    make_image(tmp_path / "a.jpg")
    (tmp_path / "notes.txt").write_text("hi")
    sub = tmp_path / "sub"
    sub.mkdir()
    make_image(sub / "c.gif")

    names = lambda files: [f.relative_to(tmp_path).as_posix() for f in files]  # noqa: E731

    assert names(collect_files([tmp_path])) == ["a.jpg", "b.png"]
    assert names(collect_files([tmp_path], recursive=True)) == ["a.jpg", "b.png", "sub/c.gif"]
    assert "notes.txt" in names(collect_files([tmp_path], all_files=True))
    # Explicit files are kept even without an image extension, and duplicates are dropped.
    assert names(collect_files([tmp_path / "notes.txt", tmp_path / "notes.txt"])) == ["notes.txt"]
    assert collect_files([tmp_path / "missing.png"]) == []


def test_jpeg_comment_goes_after_exif(tmp_path: Path) -> None:
    path = tmp_path / "exif.jpg"
    image = Image.new("RGB", (8, 8), "red")
    exif = Image.Exif()
    exif[0x010F] = "TestCamera"  # Make
    image.save(path, "JPEG", exif=exif)

    result = change_hash(path)

    with Image.open(result.output) as reopened:
        assert reopened.getexif()[0x010F] == "TestCamera"
        assert len(reopened.info["comment"]) == 32  # our random hex payload


def test_gif87a_is_upgraded_to_89a() -> None:
    data = b"GIF87a" + b"\x00" * 20 + b"\x3b"
    new_data, method = inject(data, b"abc")
    assert method == METHOD_GIF
    assert new_data == b"GIF89a" + b"\x00" * 20 + b"\x21\xfe\x03abc\x00\x3b"


def test_gif_without_trailer_falls_back_to_append() -> None:
    data = b"GIF89a" + b"\x00" * 20
    assert inject(data, b"abc") == (data + b"abc", METHOD_APPEND)


def test_other_files_get_bytes_appended() -> None:
    new_data, method = inject(b"hello", b"abc")
    assert (new_data, method) == (b"helloabc", METHOD_APPEND)


def test_broken_png_raises() -> None:
    truncated = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
    with pytest.raises(FormatError):
        inject(truncated, b"abc")
