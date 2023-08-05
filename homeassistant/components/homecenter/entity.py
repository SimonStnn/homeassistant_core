"""Support for Homecenter devices."""
from __future__ import annotations

from homecenteraio.channels import Channel as HomecenterChannel

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN


class HomecenterEntity(Entity):
    """Representation of a Homecenter entity."""

    _attr_should_poll: bool = False

    def __init__(self, channel: HomecenterChannel) -> None:
        """Initialize a Homecenter entity."""
        self._channel = channel
        self._attr_name = channel.name
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, str(channel.id)),
            },
            manufacturer="Homecenter",
            name=channel.name,
        )
        self._attr_unique_id = str(channel.id)
