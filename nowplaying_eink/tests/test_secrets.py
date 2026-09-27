import json

import pytest

from app import config, flatyaml


def test_parse_quotes_comments_and_bare_values():
    d = flatyaml.parse(
        '# comment\n\nwifi_ssid: "My Net #2"\nwifi_password: \'p:a"ss\'\ndevice_token: abc123  # trailing\nempty: ""\n'
    )
    assert d == {"wifi_ssid": "My Net #2", "wifi_password": 'p:a"ss', "device_token": "abc123", "empty": ""}


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        flatyaml.parse("just a line")
    with pytest.raises(ValueError):
        flatyaml.parse('k: "unclosed')


def test_secrets_fill_only_empty_options(tmp_path):
    opts = tmp_path / "options.json"
    opts.write_text(json.dumps({"source": "lastfm", "lastfm_user": "ofri", "lastfm_api_key": "from-options"}))
    sec = tmp_path / "secrets.yaml"
    sec.write_text('device_token: "0123456789abcdefXYZ"\nlastfm_api_key: "from-secrets"\n', encoding="utf-8")
    s = config.load(opts, sec)
    assert s.device_token == "0123456789abcdefXYZ"
    assert s.lastfm_api_key == "from-options"
