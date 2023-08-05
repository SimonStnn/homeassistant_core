"""The Homecenter integration."""
from __future__ import annotations

import logging

from homecenteraio.controller import Homecenter

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.COVER,
    Platform.CLIMATE,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Homecenter from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    controller = Homecenter(
        f"{entry.data[CONF_ADDRESS]}:{entry.data[CONF_PORT]}",
        entry.data[CONF_USERNAME],
    )
    hass.data[DOMAIN][entry.entry_id] = controller

    await controller.connect(entry.data[CONF_PASSWORD])

    await controller.request_components()
    await controller.await_components()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    controller: Homecenter = hass.data[DOMAIN][entry.entry_id]
    await controller.close()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
