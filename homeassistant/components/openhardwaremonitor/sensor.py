"""Support for Open Hardware Monitor Sensor Platform."""

from __future__ import annotations

from collections import defaultdict
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfDataRate,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfInformation,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenHardwareMonitorCoordinator

_LOGGER = logging.getLogger(__name__)

OHM_VALUE = "Value"
OHM_CHILDREN = "Children"
OHM_NAME = "Text"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Prepare sensor entities for OWM."""
    coordinator: OpenHardwareMonitorCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]
    entities: list[OpenHardwareMonitorDevice] = create_entities(coordinator)
    async_add_entities(entities, update_before_add=True)


def create_entities(
    coordinator: OpenHardwareMonitorCoordinator,
) -> list[OpenHardwareMonitorDevice]:
    """Create a list of sensor entities from current data update."""
    data: dict[str, Any] | None = coordinator.data
    if data is None:
        return []

    # Device name is the first
    device_info = None
    if data[OHM_CHILDREN] is not None and len(data[OHM_CHILDREN]) > 0:
        machine_name = data[OHM_CHILDREN][0].get(OHM_NAME)
        device_info = DeviceInfo(
            name=machine_name, model=machine_name, identifiers={(DOMAIN, machine_name)}
        )
        _LOGGER.info("Set up OpenHardwareMonitor for %s", machine_name)
    return parse_children(coordinator, data, [], [], [], defaultdict(int), device_info)


def parse_children(coordinator, json, devices, path, names, namedict, device_info):
    """Recursively loop through child objects, finding the values."""
    result = devices.copy()

    if json[OHM_CHILDREN]:
        for child_index in range(len(json[OHM_CHILDREN])):
            child_path = path.copy()
            child_path.append(child_index)

            child_names = names.copy()
            if path:
                child_names.append(json[OHM_NAME])

            obj = json[OHM_CHILDREN][child_index]

            added_devices = parse_children(
                coordinator,
                obj,
                devices,
                child_path,
                child_names,
                namedict,
                device_info,
            )

            result = result + added_devices
        return result

    if json[OHM_VALUE].find(" ") == -1:
        return result

    split_value = json[OHM_VALUE].split(" ")
    initial_value = split_value[0]
    unit_of_measurement = split_value[1]
    child_names = names.copy()
    child_names.append(json[OHM_NAME])
    # Prevent duplicate entity IDs by appending "2", "3", etc. for
    # each duplicate found.
    fullname = " ".join(child_names)
    namedict[fullname] += 1
    if namedict[fullname] > 1:
        fullname += " " + str(namedict[fullname])

    dev = OpenHardwareMonitorDevice(
        coordinator, fullname, path, unit_of_measurement, device_info
    )
    _LOGGER.debug(
        "[%s] - %s - %s %s",
        fullname,
        path,
        initial_value,
        dev.native_unit_of_measurement,
    )

    result.append(dev)
    return result


class OpenHardwareMonitorDevice(CoordinatorEntity, SensorEntity):
    """Device used to display information from OpenHardwareMonitor."""

    def __init__(self, coordinator, name, path, unit_of_measurement, device_info):
        """Initialize an OpenHardwareMonitor sensor."""
        super().__init__(coordinator)
        self.unique_id = name
        self._name = name
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self.path = path
        self.attributes = {}
        unit_of_measurement = self._sanitize_unit(unit_of_measurement)
        self._unit_of_measurement = unit_of_measurement
        self._attr_device_class = self._device_class_from_unit(unit_of_measurement)
        # OWM shows its measurements with 1 decimal
        self._attr_suggested_display_precision = 1
        self._attr_device_info = device_info
        self.value = None

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def native_value(self):
        """Return the state of the device."""
        if self.value == "-":
            return None
        return self.value

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the entity."""
        return self.attributes

    @classmethod
    def parse_number(cls, string):
        """In some locales a decimal numbers uses ',' instead of '.'."""
        return string.replace(",", ".")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if data is None:
            return

        array = data[OHM_CHILDREN]
        _attributes = {}

        for path_index, path_number in enumerate(self.path):
            values = array[path_number]

            if path_index == len(self.path) - 1:
                self.value = self.parse_number(values[OHM_VALUE].split(" ")[0])
                _attributes.update({"name": values[OHM_NAME]})
                self.attributes = _attributes
                _LOGGER.debug("%s updated to %s", self.name, self.value)
                self.async_write_ha_state()
                return
            array = array[path_number][OHM_CHILDREN]
            _attributes.update({f"level_{path_index}": values[OHM_NAME]})

    def _sanitize_unit(self, unit_of_measurement):
        """Sanitize unit of measurement.

        Some units in OWM don't quite match case to
        HASS units so we prefer to convert them for
        consistency.
        """
        if unit_of_measurement is None:
            return None

        UNIT_MAP = {
            "kb/s": UnitOfDataRate.KILOBYTES_PER_SECOND,
            "mb/s": UnitOfDataRate.MEGABYTES_PER_SECOND,
            "gb/s": UnitOfDataRate.GIGABYTES_PER_SECOND,
            "hz": UnitOfFrequency.HERTZ,
            "khz": UnitOfFrequency.KILOHERTZ,
            "mhz": UnitOfFrequency.MEGAHERTZ,
            "ghz": UnitOfFrequency.GIGAHERTZ,
            "°c": UnitOfTemperature.CELSIUS,
            "°f": UnitOfTemperature.FAHRENHEIT,
            "w": UnitOfPower.WATT,
            "gb": UnitOfInformation.GIGABYTES,
            "mb": UnitOfInformation.MEGABYTES,
            "kb": UnitOfInformation.KILOBYTES,
            "b": UnitOfInformation.BYTES,
            "v": UnitOfElectricPotential.VOLT,
        }

        unit = unit_of_measurement.lower()
        if unit in UNIT_MAP:
            return UNIT_MAP[unit]
        return unit_of_measurement

    def _device_class_from_unit(self, unit_of_measurement):
        if unit_of_measurement in ("°C", "°F"):
            return SensorDeviceClass.TEMPERATURE
        if unit_of_measurement in ("W"):
            return SensorDeviceClass.POWER
        if unit_of_measurement in ("V"):
            return SensorDeviceClass.VOLTAGE
        if unit_of_measurement in ("KB/s"):
            return SensorDeviceClass.DATA_RATE
        if unit_of_measurement in ("GB", "MB", "KB"):
            return SensorDeviceClass.DATA_SIZE
        if unit_of_measurement in ("MHz", "GHz", "KHz", "Hz"):
            return SensorDeviceClass.FREQUENCY
        return None
