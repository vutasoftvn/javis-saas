from tests.e2e.conftest import external_company_base_url


def test_external_company_base_url_requires_a_value_and_normalizes_trailing_slash(
    monkeypatch,
) -> None:
    monkeypatch.delenv("E2E_BASE_URL_COMPANY", raising=False)
    assert external_company_base_url() is None

    monkeypatch.setenv("E2E_BASE_URL_COMPANY", "http://127.0.0.1:4000/")
    assert external_company_base_url() == "http://127.0.0.1:4000"
