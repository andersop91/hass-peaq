import time
from datetime import datetime

from custom_components.peaqev.peaqservice.util.constants import (
    CHARGER,
    PARAMS,
    CURRENT,
    CHARGERID
)


class ChargerHelpers:
    def __init__(self, charger):
        self.c = charger

    async def setchargerparams(self, calls, ampoverride:int = 0) -> dict:
        amps = ampoverride if ampoverride >= 6 else self.c.hub.threshold.allowedcurrent
        serviceparams = {}
        if await self._checkchargerparams(calls) is True:
            serviceparams[calls[PARAMS][CHARGER]] = calls[PARAMS][CHARGERID]
        serviceparams[calls[PARAMS][CURRENT]] = amps
        return serviceparams

    def wait_turn_on(self) -> bool:
        while not self.c.charger_active and self.c.params.running:
            time.sleep(3)
        return self._updates_should_continue()

    def wait_update_current(self) -> bool:
        self.c.hub.sensors.chargerobject_switch.updatecurrent()
        while (self._currents_match() or self._too_late_to_change()) and self.c.params.running:
            time.sleep(3)
        return self._updates_should_continue()

    def wait_loop_cycle(self):
        timer = 120
        start_time = time.time()
        self.c.hub.sensors.chargerobject_switch.updatecurrent()
        while time.time() - start_time < timer:
            time.sleep(3)
        self.c.hub.sensors.chargerobject_switch.updatecurrent()

    def _updates_should_continue(self) -> bool:
        ret = [
            self.c.params.running is False,
            self.c.params.disable_current_updates
        ]
        return not any(ret)

    async def _checkchargerparams(self, calls) -> bool:
        return len(calls[PARAMS][CHARGER]) > 0 and len(calls[PARAMS][CHARGERID]) > 0

    def _currents_match(self) -> bool:
        return self.c.hub.sensors.chargerobject_switch.current == self.c.hub.threshold.allowedcurrent

    def _too_late_to_change(self) -> bool:
        return datetime.now().minute >= 55 and self.c.hub.threshold.allowedcurrent > self.c.hub.sensors.chargerobject_switch.current
