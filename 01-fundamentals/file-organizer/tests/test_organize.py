import json
import os
from datetime import datetime

import pytest

from organize import (LOG_NAME, apply_plan, extension_map, load_categories, make_plan,
                      undo_last)


def snapshot(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


@pytest.fixture
def messy(tmp_path):
    for name in ["photo.JPG", "notes.txt", "data.csv", "song.mp3", "app.py",
                 "backup.tar.gz", "README", ".hidden"]:
        (tmp_path / name).write_text(name)
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / "clip.mp4").write_text("clip")
    return tmp_path


def moves(root, plan):
    return {s.relative_to(root).as_posix(): d.relative_to(root).as_posix() for s, d in plan}


def test_plan_by_category(messy):
    plan = moves(messy, make_plan(messy))
    assert plan == {
        "photo.JPG": "images/photo.JPG",
        "notes.txt": "documents/notes.txt",
        "data.csv": "spreadsheets/data.csv",
        "song.mp3": "audio/song.mp3",
        "app.py": "code/app.py",
        "backup.tar.gz": "archives/backup.tar.gz",
        "README": "other/README",
    }


def test_dry_run_plan_changes_nothing(messy):
    before = snapshot(messy)
    make_plan(messy, recursive=True)
    make_plan(messy, mode="date")
    assert snapshot(messy) == before


def test_hidden_files_and_log_are_skipped(messy):
    (messy / LOG_NAME).write_text('{"runs": []}')
    names = {s.name for s, _ in make_plan(messy)}
    assert ".hidden" not in names and LOG_NAME not in names


def test_recursive_takes_files_from_subfolders(messy):
    assert "old/clip.mp4" not in moves(messy, make_plan(messy))
    assert moves(messy, make_plan(messy, recursive=True))["old/clip.mp4"] == "video/clip.mp4"


def test_by_date_uses_modification_time(tmp_path):
    f = tmp_path / "scan.pdf"
    f.write_text("x")
    stamp = datetime(2025, 3, 14, 12, 0).timestamp()
    os.utime(f, (stamp, stamp))
    assert moves(tmp_path, make_plan(tmp_path, mode="date")) == {"scan.pdf": "2025/03/scan.pdf"}


def test_collision_gets_numbered_name(tmp_path):
    (tmp_path / "documents").mkdir()
    (tmp_path / "documents" / "report.pdf").write_text("old")
    (tmp_path / "documents" / "report (1).pdf").write_text("old too")
    (tmp_path / "report.pdf").write_text("new")
    plan = moves(tmp_path, make_plan(tmp_path))
    assert plan == {"report.pdf": "documents/report (2).pdf"}


def test_collision_between_two_planned_files(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.txt").write_text("1")
    (tmp_path / "x.txt").write_text("2")
    plan = make_plan(tmp_path, recursive=True)
    destinations = sorted(d.name for _, d in plan)
    assert destinations == ["x (1).txt", "x.txt"]


def test_apply_and_undo_restore_original_tree(messy):
    before = snapshot(messy)
    contents = {p: p.read_text() for p in messy.rglob("*") if p.is_file()}

    apply_plan(messy, make_plan(messy, recursive=True))
    assert (messy / "images" / "photo.JPG").exists()
    log = json.loads((messy / LOG_NAME).read_text())
    assert len(log["runs"]) == 1

    restored, warnings = undo_last(messy)
    assert restored == 8 and warnings == []
    assert snapshot(messy) == before   # files back, created folders removed, log removed
    assert all(p.read_text() == text for p, text in contents.items())


def test_undo_reverts_only_the_last_run(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    apply_plan(tmp_path, make_plan(tmp_path))
    (tmp_path / "b.mp3").write_text("b")
    apply_plan(tmp_path, make_plan(tmp_path))

    undo_last(tmp_path)
    assert (tmp_path / "b.mp3").exists()
    assert (tmp_path / "documents" / "a.txt").exists()
    undo_last(tmp_path)
    assert (tmp_path / "a.txt").exists()
    assert not (tmp_path / LOG_NAME).exists()


def test_undo_without_log_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        undo_last(tmp_path)


def test_custom_categories(tmp_path):
    config = tmp_path / "cats.json"
    config.write_text('{"photos": ["jpg", ".PNG"]}')
    ext_map = extension_map(load_categories(config))
    assert ext_map == {".jpg": "photos", ".png": "photos"}

    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "a.png").write_text("x")
    (folder / "b.pdf").write_text("x")
    assert moves(folder, make_plan(folder, ext_map=ext_map)) == {
        "a.png": "photos/a.png", "b.pdf": "other/b.pdf"}


def test_bad_config_is_rejected(tmp_path):
    config = tmp_path / "bad.json"
    config.write_text('["not", "a", "dict"]')
    with pytest.raises(ValueError):
        load_categories(config)
