from unittest.mock import Mock

from karmabot import metrics


def test_log_metrics_sends_line_protocol(monkeypatch):
    connection = Mock()
    monkeypatch.setattr(metrics, "_get_connection", lambda: connection)

    metrics.log_metrics("m x", {"z": "z", "a": "b"}, "v", 1)

    connection.send.assert_called_once_with(b"m\\ x,a=b,z=z v=1i\n")
    connection.close.assert_called_once_with()


def test_timeit_preserves_result_and_logs_elapsed_time(monkeypatch):
    times = iter([1.0, 1.012])
    log_metrics = Mock()
    monkeypatch.setattr(metrics.time, "time", lambda: next(times))
    monkeypatch.setattr(metrics, "log_metrics", log_metrics)

    @metrics.timeit("request", {"route": "health"}, "elapsed")
    def operation():
        return "result"

    assert operation() == "result"
    log_metrics.assert_called_once_with(
        "request", {"route": "health"}, "elapsed", 12
    )
