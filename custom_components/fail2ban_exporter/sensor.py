import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.const import (
    STATE_UNKNOWN,
    UnitOfTime,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

FRIENDLY_MAP = {
    "f2b_config_jail_ban_time": ("Ban Time", "mdi:timer-lock"),
    "f2b_config_jail_find_time": ("Find Time", "mdi:timer-search"),
    "f2b_config_jail_max_retries": ("Max Retries", "mdi:counter"),
    "f2b_jail_banned_current": ("Currently Banned IPs", "mdi:lock-alert"),
    "f2b_jail_banned_total": ("Total Banned IPs", "mdi:lock-check"),
    "f2b_jail_failed_current": ("Current Failures", "mdi:alert-circle"),
    "f2b_jail_failed_total": ("Total Failures", "mdi:alert-circle-outline"),
    "f2b_errors": ("Exporter Errors", "mdi:alert"),
    "f2b_jail_count": ("Active Jails", "mdi:shield-home"),
    "f2b_up": ("Exporter Up", "mdi:cloud-check"),
    "f2b_version": ("Fail2ban Version", "mdi:information"),
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Fail2ban sensors from the coordinator."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []

    if not coordinator.data:
        _LOGGER.debug("Coordinator has no initial data, waiting for first update")
        await coordinator.async_request_refresh()

    for jail, metrics in (coordinator.data or {}).items():
        for metric_name in metrics.keys():
            sensors.append(Fail2banJailSensor(coordinator, jail, metric_name))

    async_add_entities(sensors, update_before_add=True)
    _LOGGER.debug("fail2ban sensors initialized: %s", len(sensors))


class Fail2banJailSensor(CoordinatorEntity, SensorEntity):
    """Fail2ban metric sensor actively updated from the coordinator."""

    _attr_should_poll = False
    _attr_state_class = "measurement"

    def __init__(self, coordinator, jail_name, metric_name):
        super().__init__(coordinator)
        self._jail = jail_name
        self._metric = metric_name
        self._last_value = None
        self._unsub_timer = None

        # Friendly name and icon
        friendly, icon = FRIENDLY_MAP.get(metric_name, (metric_name.replace("_", " ").title(), "mdi:chart-line"))
        self._attr_name = f"{jail_name.replace('-', ' ').title()} {friendly}"
        self._attr_icon = icon
        self._attr_unique_id = f"{DOMAIN}_{jail_name}_{metric_name}".replace("-", "_").lower()

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, jail_name)},
            name=f"Fail2ban Jail: {jail_name}" if jail_name != "global" else "Fail2ban Server",
            manufacturer="Fail2ban",
            model="Exporter",
        )

        # 📏 Units
        if "ban_time" in metric_name or "find_time" in metric_name:
            self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        elif any(k in metric_name for k in ["retries", "count", "banned", "failed"]):
            self._attr_native_unit_of_measurement = "count"
        else:
            self._attr_native_unit_of_measurement = None

    @property
    def native_value(self):
        """Return the latest numeric value from coordinator data, formatted nicely."""
        data = self.coordinator.data or {}
        jail_data = data.get(self._jail, {})
        value = jail_data.get(self._metric)

        if value is None:
            _LOGGER.debug(" [%s] No value (jail=%s metric=%s)", self._attr_name, self._jail, self._metric)
            return STATE_UNKNOWN

        # Round and clean float values
        if isinstance(value, float):
            if value.is_integer():
                value = int(value)
            else:
                value = round(value, 2)

        if self._last_value != value:
            _LOGGER.debug(" [%s] Jail=%s Metric=%s Value=%s", self._attr_name, self._jail, self._metric, value)
            self._last_value = value

        return value

    async def async_added_to_hass(self):
        """Subscribe to coordinator updates and schedule periodic refresh."""
        await super().async_added_to_hass()
        _LOGGER.debug(" Subscribing %s to coordinator updates", self._attr_name)

        def _handle_coordinator_update():
            self.async_write_ha_state()

        # Link sensor to coordinator updates
        self.async_on_remove(self.coordinator.async_add_listener(_handle_coordinator_update))

        # Periodic refresh (every 30 seconds)
        def _periodic_refresh(now):
            self.hass.add_job(self.async_write_ha_state)

        self._unsub_timer = async_track_time_interval(
            self.hass, _periodic_refresh, timedelta(seconds=30)
        )

        # Immediate initial update
        self.hass.add_job(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Cancel timers when removed."""
        if self._unsub_timer:
            self._unsub_timer()