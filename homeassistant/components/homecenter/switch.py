"""Support for Homecenter switch."""
import logging
from typing import Any

from homecenteraio.channels import Toggle as HomecenterToggle
from homecenteraio.component import Component, ComponentType
from homecenteraio.const import Event
from homecenteraio.controller import Homecenter

from homeassistant.components.switch import STATE_ON, SwitchEntity
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
    """Set up Homecenter switch based on config_entry."""
    controller: Homecenter = hass.data[DOMAIN][entry.entry_id]
    entity_map: dict[int, HomecenterEntity] = {}
    for component in controller.get_all(ComponentType.SWITCH):
        channel = HomecenterToggle(controller, component)
        entity = HomecenterSwitch(channel)

        if component.id in entity_map:
            _LOGGER.warning("Component id (%s) already in entity map", component.id)
            continue

        entity_map[component.id] = entity

    async_add_entities(list(entity_map.values()))

    def handle_status_update(component: Component, new_state: HomecenterToggle.State):
        """Event handler for status updates."""
        try:
            # find entity in entity_map
            entity = entity_map[component.id]
            if not entity:
                return _LOGGER.warning(
                    "Something went wrong when with switch entity map"
                )

            # Update hass status
            hass.states.async_set(
                entity.entity_id,
                STATE_ON if new_state.value > 0 else "off",
            )
        except AttributeError as error:
            _LOGGER.warning(error)

    controller.on(Event.STATUS_UPDATE_SWITCH, handle_status_update)


class HomecenterSwitch(HomecenterEntity, SwitchEntity):
    """Representation of a switch."""

    _channel: HomecenterToggle

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._channel.is_on()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the switch to turn on."""
        # Update channels status
        await self._channel.turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the switch to turn off."""
        # Update channels status
        await self._channel.turn_off()
