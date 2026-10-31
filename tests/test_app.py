from unittest.mock import Mock

import pytest

from karmabot import blueprint
from karmabot.errors import InvalidRequestError


@pytest.mark.parametrize("path", ["/", "/health"])
def test_health_endpoints_return_ok(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "OK"


@pytest.mark.parametrize("path", [
    "/slack_events/v1/karmabot-v1_events",
    "/slack_events/v1/karmabot_dev-v1_events",
])
def test_slack_event_endpoint_returns_challenge(client, path):
    response = client.post(path, json={
        "token": "test-token",
        "challenge": "challenge-value",
    })

    assert response.status_code == 200
    assert response.get_json() == {"challenge": "challenge-value"}


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"event": {"type": "message", "text": "hello ++"}}, 401),
        ({"token": "invalid", "event": {"type": "message", "text": "hello ++"}}, 403),
    ],
)
def test_slack_events_reject_invalid_verification_token(client, payload, expected_status):
    response = client.post("/slack_events/v1/karmabot-v1_events", json=payload)

    assert response.status_code == expected_status


def test_slack_message_with_karma_is_submitted_to_controller(client, monkeypatch):
    controller = Mock()
    submit = Mock()
    monkeypatch.setattr(blueprint, "get_karma_controller", lambda: controller)
    monkeypatch.setattr(blueprint.executor, "submit", submit)
    event = {"type": "message", "text": "hello ++"}

    response = client.post("/slack_events/v1/karmabot-v1_events", json={
        "token": "test-token",
        "event": event,
    })

    assert response.status_code == 200
    assert response.get_json() == {}
    submit.assert_called_once()
    args, _ = submit.call_args
    assert args[0] == controller.handle_event
    assert args[1]["event"] == event
    assert isinstance(args[1]["rec_time"], float)


@pytest.mark.parametrize("event", [
    {"type": "message", "text": "hello ++", "subtype": "bot_message"},
    {"type": "message", "text": "hello"},
    {"type": "app_mention", "text": "hello ++"},
])
def test_slack_events_without_dispatchable_karma_are_ignored(client, monkeypatch, event):
    submit = Mock()
    monkeypatch.setattr(blueprint.executor, "submit", submit)

    response = client.post("/slack_events/v1/karmabot-v1_events", json={
        "token": "test-token",
        "event": event,
    })

    assert response.status_code == 200
    submit.assert_not_called()


def test_app_mention_without_karma_is_submitted_to_controller(client, monkeypatch):
    controller = Mock()
    submit = Mock()
    monkeypatch.setattr(blueprint, "get_karma_controller", lambda: controller)
    monkeypatch.setattr(blueprint.executor, "submit", submit)

    response = client.post("/slack_events/v1/karmabot-v1_events", json={
        "token": "test-token",
        "event": {"type": "app_mention", "text": "hello bot"},
    })

    assert response.status_code == 200
    submit.assert_called_once()
    assert submit.call_args.args[0] == controller.handle_mention


@pytest.mark.parametrize(
    ("form", "expected_status"),
    [
        ({"command": "/karma"}, 401),
        ({"token": "invalid", "command": "/karma"}, 403),
    ],
)
def test_slash_commands_reject_invalid_verification_token(client, form, expected_status):
    response = client.post("/slack_events/v1/karmabot-v1_commands", data=form)

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    ("command", "controller_getter", "method_name"),
    [
        ("/karma", "get_karma_controller", "handle_command"),
        ("/badge", "get_badges_controller", "handle_command"),
    ],
)
def test_slash_commands_submit_to_matching_controller(
    client, monkeypatch, command, controller_getter, method_name
):
    controller = Mock()
    submit = Mock()
    monkeypatch.setattr(blueprint, controller_getter, lambda: controller)
    monkeypatch.setattr(blueprint.executor, "submit", submit)

    response = client.post("/slack_events/v1/karmabot-v1_commands", data={
        "token": "test-token",
        "command": command,
        "text": "help",
    })

    assert response.status_code == 200
    assert response.get_data(as_text=True) == ""
    submit.assert_called_once()
    assert submit.call_args.args[0] == getattr(controller, method_name)


def test_slack_interaction_requires_payload(client):
    response = client.post("/slack_events/v1/karmabot-v1_interactions")

    assert response.status_code == 401


def test_badge_creation_interaction_is_submitted(client, monkeypatch):
    controller = Mock()
    submit = Mock()
    monkeypatch.setattr(blueprint, "get_badges_controller", lambda: controller)
    monkeypatch.setattr(blueprint.executor, "submit", submit)

    response = client.post("/slack_events/v1/karmabot-v1_interactions", data={
        "payload": (
            '{"token":"test-token","type":"dialog_submission",'
            '"callback_id":"karma-badge-create-0"}'
        ),
    })

    assert response.status_code == 200
    submit.assert_called_once()
    assert submit.call_args.args[0] == controller.cmd_badge_create_complete


def test_custom_invalid_request_error_returns_json(app):
    @app.get("/test-invalid-request")
    def invalid_request():
        raise InvalidRequestError("invalid input")

    response = app.test_client().get("/test-invalid-request")

    assert response.status_code == 400
    assert response.get_json() == {"ok": False, "error": "invalid input"}


def test_unexpected_slack_error_returns_generic_server_error(client, monkeypatch):
    def raise_error():
        raise RuntimeError("internal detail")

    monkeypatch.setattr(blueprint, "get_karma_controller", raise_error)
    response = client.post("/slack_events/v1/karmabot-v1_events", json={
        "token": "test-token",
        "event": {"type": "message", "text": "hello ++"},
    })

    assert response.status_code == 500
    assert response.get_data(as_text=True) == "An internal error occurred."
