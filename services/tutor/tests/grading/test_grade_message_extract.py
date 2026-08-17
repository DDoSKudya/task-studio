from app.domain.grade.message_extract import first_plain_str


def test_first_plain_str_skips_non_strings() -> None:
    assert first_plain_str(1, None, "ok") == "ok"


def test_first_plain_str_keeps_empty() -> None:
    assert first_plain_str("") == ""
    assert first_plain_str() == ""
