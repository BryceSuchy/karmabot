import pytest

from karmabot import regex


@pytest.mark.parametrize(
    ("text", "group", "subject"),
    [
        ("coffee ++", "thing", "coffee"),
        ('"coffee break" ++', "qthing1", "coffee break"),
        ("<@U123|jane> ++", "user", "U123"),
        ("<#C123|general> ++", "channel", "C123"),
        ("<!subteam^S123|team> ++", "group", "S123"),
    ],
)
def test_karma_expression_matches_subject(text, group, subject):
    match = regex.big_match_karma_re.search(text)

    assert match is not None
    assert match.group(group) == subject
    assert match.group("karma") == "++"


@pytest.mark.parametrize("text", ["coffee +", "coffee -", "plain message"])
def test_incomplete_karma_expression_does_not_match(text):
    assert regex.big_match_karma_re.search(text) is None
