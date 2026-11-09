"""Pure helpers behind `python -m xauto add-post`."""

from datetime import timedelta

import pytest

from xauto.cli import CliError, parse_when, validate_media


def test_parse_when_applies_default_offset():
    value = parse_when("2026-11-10 19:45", "+03:00")
    assert value.utcoffset() == timedelta(hours=3)
    assert (value.hour, value.minute) == (19, 45)


def test_parse_when_keeps_explicit_offset():
    value = parse_when("2026-11-10T19:45+01:00", "+03:00")
    assert value.utcoffset() == timedelta(hours=1)


def test_parse_when_negative_offset():
    assert parse_when("2026-11-10 08:00", "-05:00").utcoffset() == timedelta(hours=-5)


def test_parse_when_rejects_garbage():
    with pytest.raises(CliError):
        parse_when("tomorrow", "+03:00")


def _touch(tmp_path, *names):
    paths = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(b"x")
        paths.append(path)
    return paths


def test_media_up_to_four_images_ok(tmp_path):
    validate_media(_touch(tmp_path, "1.png", "2.jpg", "3.webp", "4.png"))


@pytest.mark.parametrize(
    "names",
    [
        ("1.png", "2.png", "3.png", "4.png", "5.png"),   # too many images
        ("a.mp4", "b.mp4"),                              # two videos
        ("a.mp4", "b.png"),                              # mixed
        ("notes.txt",),                                  # unsupported
    ],
)
def test_media_rejected(tmp_path, names):
    with pytest.raises(CliError):
        validate_media(_touch(tmp_path, *names))


def test_media_missing_file(tmp_path):
    with pytest.raises(CliError):
        validate_media([tmp_path / "nope.mp4"])
