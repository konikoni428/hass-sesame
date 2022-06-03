"""Support for Sesame, by CANDY HOUSE."""
from __future__ import annotations

from pysesameos2.ble import CHSesame2

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import ATTR_BATTERY_LEVEL, ATTR_DEVICE_ID

from .const import DOMAIN


def get_model_name(device_model: str):
    """Convert pysesame3 device model to Real device model"""
    if device_model == "sesame_2":
        return "SESAME 3/4"
    elif device_model == "ssmbot_1":
        return "SESAME bot"
    elif device_model == "sesame_4":
        return "SESAME 3/4"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Sesame2 locks based on a config entry."""
    sesame = hass.data[DOMAIN][entry.entry_id]
    locks = []

    locks.append(Sesame2Device(hass, sesame))

    async_add_entities(locks)


class Sesame2Device(LockEntity):
    """Representation of a Sesame device."""

    def __init__(self, hass: HomeAssistant, sesame: CHSesame2) -> None:
        """Initialize the Sesame device."""
        self._sesame: CHSesame2 = sesame
        self.hass: HomeAssistant = hass

        # Cached properties from pysesame object.
        self._attr_unique_id: str | None = sesame.deviceId.replace("-", "")
        # self._attr_is_locked = sesame.mechStatus.isInLockRange()
        self._battery: int | None = None
        self.hass.async_add_executor_job(self.init_update)
        self.hass.async_add_executor_job(sesame.setDeviceStatusCallback, self._callback)

    def lock(self, **kwargs) -> None:
        """Lock the lock."""
        self._sesame.lock()

    async def async_lock(self, **kwargs) -> None:
        """Lock the lock."""
        await self.hass.async_add_executor_job(self._sesame.lock)

    def unlock(self, **kwargs) -> None:
        """Unlock the lock."""
        self._sesame.unlock()

    async def async_unlock(self, **kwargs) -> None:
        """Unlock the lock."""
        await self.hass.async_add_executor_job(self._sesame.unlock)

    @callback
    def _callback(self, device: CHSesame2) -> None:
        """Handle status update received."""
        status = device.getMechStatus()
        self._attr_is_locked = status.isInLockRange()
        self._battery = status.getBatteryPercentage()
        self.async_write_ha_state()

    def init_update(self) -> None:
        """Update the internal state of the device."""
        status = self._sesame.getMechStatus()
        self._battery = status.getBatteryPercentage()
        self._attr_is_locked = status.isInLockRange()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            # ATTR_DEVICE_ID: self._attr_unique_id,
            # ATTR_SERIAL_NO: self._serial,
            ATTR_BATTERY_LEVEL: self._battery,
        }

    @property
    def device_info(self):
        model = get_model_name(self._sesame.productModel.deviceModel())
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._attr_unique_id)
            },
            "name": f"Sesame {self._attr_unique_id}",
            "manufacturer": "CANDY HOUSE",
            "model": model,
        }

    @property
    def should_poll(self) -> bool:
        return False
