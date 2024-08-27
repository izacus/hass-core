"""The tests for the Open Hardware Monitor platform."""

import requests_mock

from homeassistant.components.openhardwaremonitor.const import DOMAIN
from homeassistant.components.sensor import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_HOST,
    CONF_PORT,
)
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry, load_fixture


async def test_setup(hass: HomeAssistant, requests_mock: requests_mock.Mocker) -> None:
    """Test for successfully setting up the platform."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "localhost",
            CONF_PORT: 8085,
        },
    )
    entry.add_to_hass(hass)

    requests_mock.get(
        "http://localhost:8085/data.json",
        text=load_fixture("openhardwaremonitor.json", "openhardwaremonitor"),
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entities = hass.states.async_entity_ids("sensor")
    assert len(entities) == 38

    state = hass.states.get("sensor.test_pc_intel_core_i7_7700_temperatures_cpu_core_1")

    assert state is not None
    assert state.state == "31.0"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "°C"
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.TEMPERATURE
    assert state.attributes.get(ATTR_STATE_CLASS) == SensorStateClass.MEASUREMENT

    state = hass.states.get("sensor.test_pc_intel_core_i7_7700_powers_cpu_package")

    assert state is not None
    assert state.state == "12.1"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "W"
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.POWER
    assert state.attributes.get(ATTR_STATE_CLASS) == SensorStateClass.MEASUREMENT

    state = hass.states.get(
        "sensor.test_pc_nvidia_geforce_gtx_1080_data_gpu_memory_free"
    )

    assert state is not None
    assert state.state == "7873.1"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "MB"
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.DATA_SIZE
    assert state.attributes.get(ATTR_STATE_CLASS) == SensorStateClass.MEASUREMENT
