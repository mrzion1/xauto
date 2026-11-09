"""Plural forms are easy to get wrong, so they get their own tests."""

import pytest

from xauto.i18n import plural, set_language


@pytest.mark.parametrize(
    "count, expected",
    [(1, "аккаунт"), (2, "аккаунта"), (4, "аккаунта"), (5, "аккаунтов"), (11, "аккаунтов"),
     (12, "аккаунтов"), (21, "аккаунт"), (22, "аккаунта"), (0, "аккаунтов"), (111, "аккаунтов")],
)
def test_russian_plural(count, expected):
    set_language("ru")
    assert plural("stats.accounts", count) == expected


def test_english_plural():
    set_language("en")
    try:
        assert plural("stats.accounts", 1) == "account"
        assert plural("stats.accounts", 3) == "accounts"
    finally:
        set_language("ru")
