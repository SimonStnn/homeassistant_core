"""Support for Homecenter cover."""
import logging
from typing import Any

from homecenteraio.channels import (
    Channel as HomecenterChannel,
    Shade as HomecenterShade,
)
from homecenteraio.component import Component, ComponentType
from homecenteraio.const import Event
from homecenteraio.controller import Homecenter

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
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
    """Set up Homecenter cover based on config_entry."""
    controller: Homecenter = hass.data[DOMAIN][entry.entry_id]
    entity_map: dict[int, HomecenterCover] = {}
    for component in controller.get_all(ComponentType.SHADE):
        entity = HomecenterCover(component.channel)

        if component.id in entity_map:
            _LOGGER.warning("Component id (%s) already in entity map", component.id)
            continue

        entity_map[component.id] = entity

    async_add_entities(list(entity_map.values()))

    def handle_status_update(component: Component, *args):
        """Event handler for status updates."""
        prev_state: HomecenterShade.State = args[0]
        new_state: HomecenterShade.State = args[1]
        try:
            # find entity in entity_map
            entity = entity_map[component.id]
            if not entity:
                return _LOGGER.warning(
                    "Something went wrong when with cover entity map"
                )

            # Update hass status
            state = hass.states.get(entity.entity_id)
            if not state:
                return _LOGGER.warning("No state found for %s", component.description)
            if not isinstance(component.channel, HomecenterShade):
                return _LOGGER.warning(
                    "Not a valid channel type for %s", component.description
                )

            new_state_attr = state.attributes.copy()
            new_state_attr["supported_features"] = (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
            )

            new_cover_state: str
            new_cover_state = component.channel.get_state(
                prev_state, new_state
            ).name.lower()

            hass.states.async_set(entity.entity_id, new_cover_state, new_state_attr)
        except AttributeError as error:
            _LOGGER.warning(error)

    controller.on(Event.STATUS_UPDATE_SHADE, handle_status_update)


class HomecenterCover(HomecenterEntity, CoverEntity):
    """Representation of a cover."""

    _channel: HomecenterShade

    def __init__(self, channel: HomecenterChannel) -> None:
        """Initialize the cover."""
        super().__init__(channel)

        self._attr_supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        )

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        return self._channel.is_closed()

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return self._channel.is_opening()

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return self._channel.is_closing()

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover."""
        return None

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self._channel.open()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self._channel.close()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self._channel.stop()
