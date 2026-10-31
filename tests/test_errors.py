import json

import pytest

from karmabot.errors import ErrorResponse, InvalidRequestError, WebhookNotFoundError


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (ErrorResponse("failure"), 500),
        (InvalidRequestError("invalid input"), 400),
        (WebhookNotFoundError("missing webhook"), 404),
    ],
)
def test_error_response_contains_message_and_status(error, status_code):
    response = error.to_response()

    assert response.status_code == status_code
    assert json.loads(response.get_data(as_text=True)) == {
        "ok": False,
        "error": error.message,
    }
