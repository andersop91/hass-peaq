from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from custom_components.peaqev.peaqservice.hub.hub import HomeAssistantHub
import logging

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.restore_state import RestoreEntity

import custom_components.peaqev.peaqservice.util.extensionmethods as ex
from custom_components.peaqev.const import DOMAIN
from custom_components.peaqev.sensors.sensorbase import SensorBase

_LOGGER = logging.getLogger(__name__)


class PeaqPeakSensor(SensorBase, RestoreEntity):
    device_class = SensorDeviceClass.ENERGY
    unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, hub:HomeAssistantHub, entry_id):
        self._name = f'{hub.hubname} peak'
        self._charged_peak = 0
        self._peaks_dict: dict = {}
        self._observed_peak = 0
        self._history: dict = {}
        super().__init__(hub, self._name, entry_id)

    @property
    def state(self) -> float:
        try:
            return round(float(self._charged_peak), 1)
        except:
            return 0

    async def async_update(self) -> None:
        self._charged_peak = self.hub.sensors.current_peak.charged_peak
        _peaks_dict = self.hub.sensors.current_peak.current_peaks_dictionary
        if self._peaks_dict != _peaks_dict:
            self._peaks_dict = _peaks_dict
        self._observed_peak = self.hub.sensors.current_peak.observed_peak
        self._history = self.hub.sensors.current_peak.history

    @property
    def extra_state_attributes(self) -> dict:
        attr_dict = {
            'observed_peak': float(self._observed_peak),
            'peaks_dictionary': self.set_peaksdict(),
            'peaks_history': self._history,
        }
        if self.hub.options.use_peak_history:
            attr_dict['Use startpeak from last year'] = True
        return attr_dict

    @property
    def icon(self) -> str:
        return 'mdi:chart-donut-variant'

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f'{DOMAIN}_{self._entry_id}_{ex.nametoid(self._name)}'

    @property
    def device_info(self):
        return {'identifiers': {(DOMAIN, self.hub.hub_id)}}

    def set_peaksdict(self) -> dict:
        ret = {}
        if len(self._peaks_dict) > 0:
            ret['m'] = self._peaks_dict['m']
            ret['p'] = self._peaks_dict['p']
        return ret

    async def async_added_to_hass(self):
        state = await super().async_get_last_state()
        if state:
            _LOGGER.debug('last state of %s = %s', self._name, state)
            self._charged_peak = state.state
            self._peaks_dict = state.attributes.get('peaks_dictionary', {})
            await self.hub.async_set_init_dict(self._peaks_dict)
            self._observed_peak = state.attributes.get('observed_peak', 0)
            _history = state.attributes.get('peaks_history', {})
            if len(_history):
                _dto = {}
                for k, v in _history.items():
                    _dto[datetime(year=int(k.split('_')[0]), month=int(k.split('_')[1]), day=1)] = v
                mykeys = list(_dto.keys())
                mykeys.sort(reverse=True)
                sorted_dict: dict[datetime, list[float]] = {i: _dto[i] for i in mykeys}
                _history = {f'{k.year}_{k.month}': v for k, v in sorted_dict.items()}
                self._history = _history
                self.hub.sensors.current_peak.import_from_service(_history)
        else:
            self._charged_peak = 0
            self._peaks_dict = {}
            self._observed_peak = 0
