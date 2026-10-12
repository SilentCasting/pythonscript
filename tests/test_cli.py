from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import make_image

from changeimagehash.cli import main


def test_cli_saves_copies(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    make_image(tmp_path / "a.png")
    make_image(tmp_path / "b.jpg")

    assert main([str(tmp_path)]) == 0

    assert (tmp_path / "a_unique.png").exists()
    assert (tmp_path / "b_unique.jpg").exists()
    assert "Done: 2 changed, 0 failed." in capsys.readouterr().out


def test_cli_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    image = make_image(tmp_path / "a.png")

    assert main([str(image), "--overwrite", "--json"]) == 0

    [entry] = json.loads(capsys.readouterr().out)
    assert entry["source"] == entry["output"] == str(image)
    assert entry["md5_before"] != entry["md5_after"]


def test_cli_nothing_found(tmp_path: Path) -> None:
    assert main([str(tmp_path)]) == 2


def test_cli_rejects_overwrite_with_output_dir(tmp_path: Path) -> None:
    image = make_image(tmp_path / "a.png")
    assert main([str(image), "--overwrite", "-o", str(tmp_path / "out")]) == 2
