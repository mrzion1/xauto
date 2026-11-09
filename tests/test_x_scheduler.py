"""The payload guard is what stops a wrong post from reaching X, so test it hard."""

from xauto.services.x_scheduler import _Expected, check_payload

TEXT = "line one\n\nline two"


def _payload(execute_at=1_700_000_000, status=TEXT, media=("m1",)):
    # Shape modelled on X's GraphQL request: values nested under variables.
    return {"variables": {"post_tweet_request": {"status": status, "media_ids": list(media)},
                          "execute_at": execute_at}}


def _expected(**kw):
    base = dict(execute_at=1_700_000_000, text=TEXT, media_count=1, dry_run=False)
    base.update(kw)
    return _Expected(**base)


def test_matching_payload_passes():
    assert check_payload(_payload(), _expected()) == []


def test_small_clock_difference_is_fine():
    assert check_payload(_payload(execute_at=1_700_000_030), _expected()) == []


def test_wrong_time_is_rejected():
    problems = check_payload(_payload(execute_at=1_700_000_000 + 3600), _expected())
    assert any("wrong send time" in p for p in problems)


def test_changed_text_is_rejected():
    assert check_payload(_payload(status="line one\nline two"), _expected())


def test_trailing_spaces_are_ignored():
    assert check_payload(_payload(status="line one  \n\nline two \n"), _expected()) == []


def test_missing_media_is_rejected():
    assert check_payload(_payload(media=()), _expected())


def test_unknown_payload_shape_fails_safe():
    problems = check_payload({"something": "else"}, _expected())
    assert len(problems) == 3
