import pytest

from karmabot import create_app
from karmabot import blueprint
from karmabot import metrics


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(blueprint, "log_metrics", lambda *args, **kwargs: None)
    monkeypatch.setattr(metrics, "log_metrics", lambda *args, **kwargs: None)

    app = create_app()
    app.config.update(TESTING=True, VERIFICATION_TOKEN="test-token")
    return app


@pytest.fixture
def client(app):
    return app.test_client()
