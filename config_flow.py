import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_URL

_LOGGER = logging.getLogger(__name__)

async def _test_connection(url: str) -> bool:
    """Check if exporter URL is reachable and returns valid metrics."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return "f2b_" in text  # quick sanity check
    except Exception as e:
        _LOGGER.warning("Connection test failed for %s: %s", url, e)
    return False


class Fail2banConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fail2ban Exporter."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            url = user_input[CONF_URL]
            if await _test_connection(url):
                return self.async_create_entry(
                    title="Fail2ban Exporter",
                    data={CONF_URL: url},
                )
            errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required(CONF_URL, default=DEFAULT_URL): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
