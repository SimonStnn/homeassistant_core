"""Support for Homecenter thermostat."""
import logging
from typing import Any

from homecenteraio.channels import (
    Channel as HomecenterChannel,
    Thermostat as HomecenterThermostat,
)
from homecenteraio.component import Component, ComponentType
from homecenteraio.const import Event
from homecenteraio.controller import Homecenter

from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import HomecenterEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecenter climate based on config_entry."""
    controller: Homecenter = hass.data[DOMAIN][entry.entry_id]
    entity_map: dict[int, HomecenterClimate] = {}
    for component in controller.get_all(ComponentType.THERMOSTAT):
        entity = HomecenterClimate(component.channel)

        if component.id in entity_map:
            _LOGGER.warning("Component id (%s) already in entity map", component.id)
            continue

        entity_map[component.id] = entity

    async_add_entities(list(entity_map.values()))

    def handle_status_update(component: Component, *args: Any):
        """Event handler for status updates."""
        current_temp: float = args[0]
        set_preset: str = args[1]
        set_temperature: float = args[2]
        mode: HomecenterThermostat.Mode = args[3]
        try:
            # find entity in entity_map
            entity = entity_map[component.id]
            if not entity:
                return _LOGGER.warning(
                    "Something went wrong when with climate entity map"
                )

            # Update hass status
            state = hass.states.get(entity.entity_id)
            if not state:
                return _LOGGER.warning("No state found for %s", component.description)

            new_attributes = state.attributes.copy()
            new_attributes[ATTR_CURRENT_TEMPERATURE] = current_temp
            new_attributes[ATTR_PRESET_MODE] = set_preset
            new_attributes[ATTR_TEMPERATURE] = set_temperature
            new_attributes[ATTR_HVAC_MODE] = HVACMode[mode.name.upper()]

            hass.states.async_set(
                entity.entity_id,
                "off" if mode == HomecenterThermostat.Mode.OFF else "on",
                new_attributes,
            )
        except AttributeError as error:
            _LOGGER.warning(error)

    controller.on(Event.STATUS_UPDATE_THERMOSTAT, handle_status_update)


class HomecenterClimate(HomecenterEntity, ClimateEntity):
    """Representation of a Homecenter thermostat."""

    _channel: HomecenterThermostat
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    @property
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        return self._channel.target_temperature

    @property
    def preset_mode(self) -> str | None:
        """Return the current Preset for this channel."""
        return self._channel.current_preset

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._channel.current_temperature

    def __init__(self, channel: HomecenterChannel) -> None:
        """Initialize the climate."""
        super().__init__(channel)
        # Set preset modes
        self._attr_preset_modes = self._channel.presets

        # Set the hvac modes
        hvac_modes: list[HVACMode] = []
        if HomecenterThermostat.Mode.OFF in self._channel.modes:
            hvac_modes.append(HVACMode.OFF)
        if HomecenterThermostat.Mode.AUTO in self._channel.modes:
            hvac_modes.append(HVACMode.AUTO)
        if HomecenterThermostat.Mode.HEAT in self._channel.modes:
            hvac_modes.append(HVACMode.HEAT)
        if HomecenterThermostat.Mode.COOL in self._channel.modes:
            hvac_modes.append(HVACMode.COOL)
        self._attr_hvac_modes = hvac_modes

        # Set the
        match self._channel.current_mode:
            case HomecenterThermostat.Mode.HEAT:
                self._attr_hvac_mode = HVACMode.HEAT
            case HomecenterThermostat.Mode.COOL:
                self._attr_hvac_mode = HVACMode.COOL
            case HomecenterThermostat.Mode.AUTO:
                self._attr_hvac_mode = HVACMode.AUTO
            case HomecenterThermostat.Mode.OFF:
                self._attr_hvac_mode = HVACMode.OFF
            case _:
                self._attr_hvac_mode = HVACMode.HEAT

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperatures."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self._channel.set_target_temperature(float(temp))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the new preset mode."""
        await self._channel.set_preset(preset_mode)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        await self._channel.set_hvac_mode(HomecenterThermostat.Mode[hvac_mode.name])
