from unittest.mock import MagicMock, patch

def _resp(json_data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    return m

def test_translate_parses_numbered_lines(mocker):
    from api.openrouter_provider import OpenRouterProvider
    content = "1. Tanaka Miku\n2. First Shoot"
    mocker.patch("httpx.post", return_value=_resp({
        "choices": [{"message": {"content": content}}]
    }))
    p = OpenRouterProvider("key", "google/gemini-flash-1.5")
    result = p.translate(["田中美久", "初めての撮影"])
    assert result[0] == "Tanaka Miku"
    assert result[1] == "First Shoot"

def test_translate_pads_short_response(mocker):
    from api.openrouter_provider import OpenRouterProvider
    mocker.patch("httpx.post", return_value=_resp({
        "choices": [{"message": {"content": "1. Only One"}}]
    }))
    p = OpenRouterProvider("key", "model")
    result = p.translate(["text1", "text2"])
    assert len(result) == 2
    assert result[1] == "text2"  # padded with original

def test_list_models(mocker):
    from api.openrouter_provider import OpenRouterProvider
    mocker.patch("httpx.get", return_value=_resp({
        "data": [{"id": "openai/gpt-4o"}, {"id": "anthropic/claude-3"}]
    }))
    models = OpenRouterProvider("key", "model").list_models()
    assert "openai/gpt-4o" in models

def test_test_connection_ok(mocker):
    from api.openrouter_provider import OpenRouterProvider
    mocker.patch("httpx.get", return_value=_resp({"data": [{"id": "m1"}, {"id": "m2"}]}))
    r = OpenRouterProvider("key", "model").test_connection()
    assert r["ok"] is True
    assert "2 models" in r["message"]
