from datetime import timezone
from unittest.mock import Mock

from karmabot.controller.badges import BadgesController
from karmabot.controller.karma import KarmaController


def test_ratelimit_count_uses_workspace_and_gifter_filter():
    collection = Mock()
    collection.count_documents.return_value = 7
    controller = KarmaController.__new__(KarmaController)
    controller.mongodb = {"workspace": collection}

    assert controller.ratelimit_count("workspace", "U123") == 7

    query = collection.count_documents.call_args.args[0]
    date_filter = query["$and"][0]["date"]["$gt"]
    assert date_filter.tzinfo is timezone.utc
    assert query["$and"][1] == {"gifter": {"$eq": "U123"}}


def test_get_top_karma_formats_subject_types():
    collection = Mock()
    collection.aggregate.return_value = [
        {"_id": {"type": "user", "subject": "U123"}, "total": 4},
        {"_id": {"type": "channel", "subject": "C123"}, "total": 3},
        {"_id": {"type": "thing", "subject": "coffee"}, "total": 2},
        {"_id": {"type": "group", "subject": "S123"}, "total": 1},
    ]
    controller = KarmaController.__new__(KarmaController)
    controller.mongodb = {"workspace": collection}

    result = controller.get_top_karma("workspace")

    assert result == (
        "\n4  <@U123> (user)"
        "\n3  <#C123> (channel)"
        "\n2  coffee (thing)"
        "\n1  <!subteam^S123> (group)"
    )
    pipeline = collection.aggregate.call_args.args[0]
    assert pipeline[0] == {"$match": {"$or": [
        {"type": "thing"},
        {"type": "user"},
        {"type": "channel"},
        {"type": "group"},
    ]}}
    assert pipeline[-1] == {"$limit": 10}


def test_get_top_karma_filters_by_gifter_and_type():
    collection = Mock()
    collection.aggregate.return_value = []
    controller = KarmaController.__new__(KarmaController)
    controller.mongodb = {"workspace": collection}

    assert controller.get_top_karma(
        "workspace", gifter="U123", ktype="thing", direction=1, limit=5
    ) == ""

    pipeline = collection.aggregate.call_args.args[0]
    assert pipeline[0] == {"$match": {"gifter": "U123", "type": "thing"}}
    assert pipeline[2] == {"$sort": {"total": 1}}
    assert pipeline[3] == {"$limit": 5}


def test_get_subject_count_returns_zero_for_empty_aggregation():
    collection = Mock()
    collection.aggregate.return_value = []
    controller = KarmaController.__new__(KarmaController)
    controller.mongodb = {"workspace": collection}

    assert controller.get_subject_count("workspace", None) == 0


def test_get_subject_count_returns_aggregation_result():
    collection = Mock()
    collection.aggregate.return_value = [{"total_subjects": 4}]
    controller = KarmaController.__new__(KarmaController)
    controller.mongodb = {"workspace": collection}

    assert controller.get_subject_count("workspace", None) == 4


def test_get_gifters_returns_user_and_karma_totals():
    collection = Mock()
    collection.aggregate.return_value = [
        {"_id": "U123", "total": 4},
        {"_id": "U456", "total": 2},
    ]
    controller = KarmaController.__new__(KarmaController)
    controller.mongodb = {"workspace": collection}

    assert controller.get_gifters("workspace", "thing", "coffee") == [
        ("U123", 4),
        ("U456", 2),
    ]


def test_get_badges_returns_badge_values():
    collection = Mock()
    collection.find.return_value = [{"badge": ":coffee:"}, {"badge": ":star:"}]
    controller = BadgesController.__new__(BadgesController)
    controller.mongodb = {"workspace": collection}

    assert controller.get_badges("workspace", "U123") == [":coffee:", ":star:"]
    collection.find.assert_called_once_with({"type": "badge", "subject": "U123"})


def test_can_badge_denies_nonmembers_of_badge_owner_group(app, monkeypatch):
    controller = BadgesController.__new__(BadgesController)
    controller.get_badge_info = Mock(return_value={"owner": "S123"})
    user_group_members = Mock(return_value={"ok": True, "users": ["U456"]})
    monkeypatch.setattr(
        "karmabot.controller.badges.slack_client.user_group_members",
        user_group_members,
    )

    with app.app_context():
        assert controller.can_badge("workspace", "U123", ":coffee:") is False

    user_group_members.assert_called_once_with("workspace", "S123")


def test_can_badge_allows_badge_owner_and_group_members(app, monkeypatch):
    controller = BadgesController.__new__(BadgesController)
    controller.get_badge_info = Mock(return_value={"owner": "S123"})
    user_group_members = Mock(return_value={"ok": True, "users": ["U456"]})
    monkeypatch.setattr(
        "karmabot.controller.badges.slack_client.user_group_members",
        user_group_members,
    )

    with app.app_context():
        assert controller.can_badge("workspace", "S123", ":coffee:") is True
        assert controller.can_badge("workspace", "U456", ":coffee:") is True
