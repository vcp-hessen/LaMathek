import os

import pytest

from lamathek.config import Config, _instance_timezone_from_env
from lamathek.timezone import DEFAULT_INSTANCE_TIMEZONE


def test_instance_timezone_env_default():
    assert Config.INSTANCE_TIMEZONE == DEFAULT_INSTANCE_TIMEZONE


def test_instance_timezone_env_override(monkeypatch):
    monkeypatch.setenv("LAMATHEK_INSTANCE_TIMEZONE", "Europe/Vienna")
    assert _instance_timezone_from_env() == "Europe/Vienna"


def test_instance_timezone_env_invalid(monkeypatch):
    monkeypatch.setenv("LAMATHEK_INSTANCE_TIMEZONE", "Not/A/Zone")
    with pytest.raises(ValueError, match="invalid_instance_timezone"):
        _instance_timezone_from_env()
