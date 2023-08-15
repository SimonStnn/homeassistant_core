"""Support for Homecenter light."""
from __future__ import annotations

import logging
from typing import Any

from homecenteraio.channels import Dimmer as HomecenterDimmer
from homecenteraio.component import Component, ComponentType
from homecenteraio.const import Event
from homecenteraio.controller import Homecenter

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import HomecenterEntity

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecenter light based on config_entry."""
    controller: Homecenter = hass.data[DOMAIN][entry.entry_id]
    entity_map: dict[int, HomecenterLight] = {}
    for component in controller.get_all(ComponentType.LIGHT):
        channel = HomecenterDimmer(controller, component)
        entity = HomecenterLight(channel)

        if component.id in entity_map:
            _LOGGER.warning("Component id (%s) already in entity map", component.id)
            continue

        entity_map[component.id] = entity

    async_add_entities(list(entity_map.values()))

    def handle_status_update(component: Component, *args: Any):
        """Event handler for status updates."""
        new_state: int = args[0]
        try:
            # find entity in entity_map
            entity = entity_map[component.id]
            if not entity:
                return _LOGGER.warning(
                    "Something went wrong when with light entity map"
                )

            # Update hass status
            state = hass.states.get(entity.entity_id)
            if not state:
                return _LOGGER.warning("No state found for %s", component.description)
            # Update brightness
            new_state_attr = state.attributes.copy()
            new_state_attr[ATTR_BRIGHTNESS] = new_state * 255 / 200
            # Save changes
            hass.states.async_set(
                entity.entity_id,
                "on" if new_state > 0 else "off",
                new_state_attr,
            )
        except AttributeError as error:
            _LOGGER.warning(error)

    # Register new event handler
    controller.on(Event.STATUS_UPDATE_LIGHT, handle_status_update)


class HomecenterLight(HomecenterEntity, LightEntity):
    """Representation of a Homecenter light."""

    _channel: HomecenterDimmer
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.TRANSITION

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._channel.is_on()

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return int((self._channel.brightness * 255) / 200)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the Homecenter light to turn on."""
        # Update channels status
        if ATTR_BRIGHTNESS in kwargs:
            # User specified a brightness
            await self._channel.set_brightness(
                int((int(kwargs[ATTR_BRIGHTNESS]) * 200) / 255)
            )
        else:
            # Toggle button is clicked
            await self._channel.restore_brightness()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the Homecenter light to turn off."""
        # Update channels status
        await self._channel.set_brightness(0)
