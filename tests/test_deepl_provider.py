import pytest
from unittest.mock import patch, MagicMock


def _mock_response(json_data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    if status >= 400:
        import httpx
        m.raise_for_status.side_effect = httpx.HTTPStatusError("err", request=MagicMock(), response=m)
    return m


def test_translate_batch(mocker):
    from api.deepl_provider import DeepLProvider
    mock_post = mocker.patch("httpx.post", return_value=_mock_response({
        "translations": [{"text": "Hello"}, {"text": "World"}]
    }))
    p = DeepLProvider("testkey:fx")
    result = p.translate(["こんにちは", "世界"])
    assert result == ["Hello", "World"]
    call_json = mock_post.call_args.kwargs["json"]
    assert call_json["target_lang"] == "EN"
    assert call_json["text"] == ["こんにちは", "世界"]


def test_translate_empty_returns_empty(mocker):
    from api.deepl_provider import DeepLProvider
    p = DeepLProvider("testkey:fx")
    assert p.translate([]) == []


def test_free_key_uses_free_url(mocker):
    from api.deepl_provider import DeepLProvider, FREE_BASE
    mock_post = mocker.patch("httpx.post", return_value=_mock_response({"translations": [{"text": "x"}]}))
    DeepLProvider("mykey:fx").translate(["test"])
    assert FREE_BASE in mock_post.call_args.args[0]


def test_pro_key_uses_pro_url(mocker):
    from api.deepl_provider import DeepLProvider, PRO_BASE
    mock_post = mocker.patch("httpx.post", return_value=_mock_response({"translations": [{"text": "x"}]}))
    DeepLProvider("mykey-pro").translate(["test"])
    assert PRO_BASE in mock_post.call_args.args[0]


def test_test_connection_ok(mocker):
    from api.deepl_provider import DeepLProvider
    mocker.patch("httpx.get", return_value=_mock_response({
        "character_count": 12000, "character_limit": 500000
    }))
    result = DeepLProvider("testkey:fx").test_connection()
    assert result["ok"] is True
    assert "488,000" in result["quota"]


def test_test_connection_fail(mocker):
    from api.deepl_provider import DeepLProvider
    mocker.patch("httpx.get", side_effect=Exception("timeout"))
    result = DeepLProvider("testkey:fx").test_connection()
    assert result["ok"] is False
