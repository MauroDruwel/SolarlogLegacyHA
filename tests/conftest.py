"""Fixtures for Solar-Log Legacy tests."""
from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solarlog_legacy.const import CONF_HOST, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="192.168.1.50",
        data={CONF_HOST: "192.168.1.50"},
        entry_id="solarlog_test_entry_id",
        unique_id="192.168.1.50",
    )
