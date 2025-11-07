import asyncio
import logging
from datetime import timedelta
import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import Platform
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass, entry):
    """Set up Fail2ban Exporter integration."""
    url = entry.data.get("url", "http://localhost:9191/metrics")
    _LOGGER.debug("Fail2ban Exporter setup started — URL: %s", url)

    coordinator = Fail2banDataUpdateCoordinator(hass, url)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("Fail2ban Exporter setup complete — coordinator ready")
    return True


async def async_unload_entry(hass, entry):
    """Unload Fail2ban Exporter config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class Fail2banDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Fail2ban metrics."""

    def __init__(self, hass, url):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.url = url

    async def _async_update_data(self):
        """Fetch data from Fail2ban exporter."""
        _LOGGER.debug("Fetching metrics from %s", self.url)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=10) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"HTTP {resp.status}")
                    text = await resp.text()
        except Exception as err:
            raise UpdateFailed(f"Request error: {err}") from err

        data = {}
        skipped = 0

        for line in text.splitlines():
            if not line or line.startswith("#"):
                continue

            # Only process Fail2ban metrics
            if not line.startswith("f2b_"):
                skipped += 1
                continue

            try:
                metric, value_str = line.split(" ", 1)
                value = float(value_str)
                if "{" in metric:
                    name, labels = metric.split("{", 1)
                    labels = labels.rstrip("}")
                    label_dict = dict(
                        l.split("=", 1) for l in labels.split(",") if "=" in l
                    )
                    jail = label_dict.get("jail", "global").strip('"')
                else:
                    name = metric
                    jail = "global"
                data.setdefault(jail, {})[name] = value
            except Exception:
                continue

        jails = ", ".join(data.keys())
        _LOGGER.debug("Parsed %s jails from exporter", len(data))
        _LOGGER.debug("Jails: %s", jails)
        _LOGGER.debug("Coordinator data sample: %s", str(list(data.items())[:2]))
        _LOGGER.debug("Skipped %s non-f2b metrics", skipped)

        # Notify entities that are ready
        domain_data = self.hass.data.get(DOMAIN, {})
        for entry_id, maybe_coordinator in list(domain_data.items()):
            sensor_list = self.hass.data[DOMAIN].get(f"{entry_id}_sensors")
            if sensor_list:
                for entity in sensor_list:
                    if hasattr(entity, "entity_id") and entity.entity_id:
                        try:
                            entity.async_write_ha_state()
                        except Exception as e:
                            _LOGGER.warning("Could not update entity %s: %s", entity.entity_id, e)

        return data