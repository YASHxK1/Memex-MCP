import pytest

from memex_mcp import config


def _clear_env(monkeypatch):
    for name in ("MEMEX_BACKEND_URL", "MEMEX_API_TOKEN", "MCP_HOST", "MCP_PORT", "PORT",
                 "MCP_ALLOWED_HOSTS", "MCP_ALLOWED_ORIGINS"):
        monkeypatch.delenv(name, raising=False)


def test_server_config_defaults(monkeypatch):
    _clear_env(monkeypatch)
    assert config.load_server_config([]) == config.ServerConfig("stdio", "127.0.0.1", 8000)


def test_server_config_from_environment(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_PORT", "9001")
    assert config.load_server_config([]) == config.ServerConfig("stdio", "0.0.0.0", 9001)


def test_server_config_cli_overrides_environment(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("MCP_HOST", "127.0.0.2")
    monkeypatch.setenv("MCP_PORT", "9001")
    result = config.load_server_config(
        ["--transport", "http", "--host", "0.0.0.0", "--port", "8080"]
    )
    assert result == config.ServerConfig("http", "0.0.0.0", 8080)


def test_platform_port_is_a_fallback(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PORT", "10000")
    assert config.load_server_config([]).port == 10000


def test_mcp_port_takes_precedence_over_platform_port(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("MCP_PORT", "9000")
    assert config.load_server_config([]).port == 9000


@pytest.mark.parametrize("value", ["0", "65536", "not-a-number"])
def test_invalid_port_is_rejected(monkeypatch, value):
    _clear_env(monkeypatch)
    monkeypatch.setenv("MCP_PORT", value)
    with pytest.raises(SystemExit):
        config.load_server_config([])


def test_invalid_transport_is_rejected():
    with pytest.raises(SystemExit):
        config.load_server_config(["--transport", "sse"])


def test_backend_url_defaults_and_strips_trailing_slash(monkeypatch):
    _clear_env(monkeypatch)
    assert config.backend_url() == "http://127.0.0.1:8000"
    monkeypatch.setenv("MEMEX_BACKEND_URL", "https://memex.example.com/")
    assert config.backend_url() == "https://memex.example.com"


def test_api_token_is_required(monkeypatch):
    _clear_env(monkeypatch)
    with pytest.raises(RuntimeError, match="MEMEX_API_TOKEN must be set"):
        config.api_token()
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret")
    assert config.api_token() == "secret"


def test_allowed_header_lists_are_optional_and_parsed(monkeypatch):
    _clear_env(monkeypatch)
    assert config.allowed_hosts() == []
    assert config.allowed_origins() == []
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "memex.example.com, memex.onrender.com:*")
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://memex.example.com")
    assert config.allowed_hosts() == ["memex.example.com", "memex.onrender.com:*"]
    assert config.allowed_origins() == ["https://memex.example.com"]
