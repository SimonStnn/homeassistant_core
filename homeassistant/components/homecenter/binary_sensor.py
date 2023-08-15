"""Support for Homecenter binary sensor."""
import logging
from typing import Any

from homecenteraio.channels import Input as HomecenterInput
from homecenteraio.component import Component, ComponentType
from homecenteraio.const import Event
from homecenteraio.controller import Homecenter

from homeassistant.components.binary_sensor import (
    STATE_OFF,
    STATE_ON,
    BinarySensorEntity,
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
    """Set up Homecenter binary sensor based on config_entry."""
    controller: Homecenter = hass.data[DOMAIN][entry.entry_id]
    entity_map: dict[int, HomecenterBinarySensor] = {}
    for component in controller.get_all(ComponentType.INPUT):
        channel = HomecenterInput(controller, component)
        entity = HomecenterBinarySensor(channel)

        if component.id in entity_map:
            _LOGGER.warning("Component id (%s) already in entity map", component.id)
            continue

        entity_map[component.id] = entity

    async_add_entities(list(entity_map.values()))

    def handle_status_update(component: Component, *args: Any) -> None:
        """Event handler for status updates."""
        new_state: HomecenterInput.State = args[0]
        try:
            # find entity in entity_map
            entity = entity_map[component.id]
            if not entity:
                return _LOGGER.warning(
                    "Something went wrong when with binary sensor entity map"
                )

            hass.states.async_set(
                entity.entity_id,
                STATE_ON if new_state == HomecenterInput.State.ON else STATE_OFF,
            )
        except AttributeError as error:
            _LOGGER.warning(error)

    controller.on(Event.STATUS_UPDATE_INPUT, handle_status_update)


class HomecenterBinarySensor(HomecenterEntity, BinarySensorEntity):
    """Representation of a binary sensor."""

    _channel: HomecenterInput

    @property
    def is_on(self) -> bool:
        """Return true if the sensor is on."""
        return self._channel.is_high()
