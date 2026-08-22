from unittest.mock import patch, MagicMock
from integrations.llm_providers.openrouter_service import fetch_openrouter_key_info


@patch.dict("os.environ", {"OPENROUTER_API_KEY": ""})
def test_fetch_openrouter_key_info_unconfigured():
    info = fetch_openrouter_key_info(api_key="")
    assert info["configured"] is False
    assert info["limit"] is None



@patch("httpx.Client.get")
def test_fetch_openrouter_key_info_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "label": "My Key",
            "limit": 100.0,
            "limit_remaining": 85.5,
            "usage": 14.5,
            "is_free_tier": False,
        }
    }
    mock_get.return_value = mock_resp

    info = fetch_openrouter_key_info(api_key="sk-or-v1-testkey")
    assert info["configured"] is True
    assert info["label"] == "My Key"
    assert info["limit"] == 100.0
    assert info["limit_remaining"] == 85.5
    assert info["usage"] == 14.5
    assert info["is_free_tier"] is False
