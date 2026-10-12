"""Shared fixtures: small real images in every supported format."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

# Pillow format name for each extension we generate in tests.
FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".gif": "GIF",
    ".webp": "WEBP",
    ".bmp": "BMP",
    ".tiff": "TIFF",
}


def make_image(path: Path) -> Path:
    """Write a small gradient image so every format has real pixel data."""
    image = Image.new("RGB", (32, 24))
    image.putdata([(x * 8, y * 10, 128) for y in range(24) for x in range(32)])
    image.save(path, FORMATS[path.suffix])
    return path


@pytest.fixture(params=sorted(FORMATS))
def image_file(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    return make_image(tmp_path / f"sample{request.param}")
