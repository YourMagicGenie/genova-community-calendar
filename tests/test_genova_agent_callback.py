from urllib.error import URLError

from scripts import post_genova_agent_callback as callback


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_callback_retries_temporary_network_failure(monkeypatch):
    attempts = []
    delays = []

    def fake_urlopen(_request, timeout):
        assert timeout == 20
        attempts.append(True)
        if len(attempts) == 1:
            raise URLError("temporary failure")
        return FakeResponse()

    monkeypatch.setenv("GENOVA_AGENT_CALLBACK_TOKEN", "callback-secret-0123456789abcdef")
    monkeypatch.setattr(callback, "urlopen", fake_urlopen)
    monkeypatch.setattr(callback.time, "sleep", delays.append)

    callback.send_callback({"status": "running"})

    assert len(attempts) == 2
    assert delays == [1]


def test_callback_does_not_retry_permanent_http_error(monkeypatch):
    from urllib.error import HTTPError

    attempts = []

    def fake_urlopen(_request, timeout):
        attempts.append(True)
        raise HTTPError("https://example.org/callback", 401, "unauthorized", {}, None)

    monkeypatch.setenv("GENOVA_AGENT_CALLBACK_TOKEN", "callback-secret-0123456789abcdef")
    monkeypatch.setattr(callback, "urlopen", fake_urlopen)

    try:
        callback.send_callback({"status": "running"})
    except ValueError as error:
        assert "HTTP 401" in str(error)
    else:
        raise AssertionError("a permanent callback rejection must fail")

    assert len(attempts) == 1
