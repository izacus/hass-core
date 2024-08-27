"""Constants for OpenHardwareMonitor integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "openhardwaremonitor"
PLATFORMS: list[Platform] = [Platform.SENSOR]

SCAN_INTERVAL = timedelta(seconds=30)
