import logging

from peaqevcore.models.chargecontroller_states import ChargeControllerStates
from peaqevcore.services.chargecontroller.chargecontrollerbase import ChargeControllerBase as _core

from custom_components.peaqev.peaqservice.chargecontroller.chargecontroller_helpers import defer_start
from custom_components.peaqev.peaqservice.chargecontroller.ichargecontroller import IChargeController

_LOGGER = logging.getLogger(__name__)


class ChargeController(IChargeController):
    def __init__(self, hub, charger_states):
        super().__init__(hub, charger_states)
        self._core = _core(charger_state_translation=charger_states)

    @property
    def below_startthreshold(self) -> bool:
        return self._core._below_start_threshold(
            predicted_energy=self.hub.prediction.predictedenergy,
            current_peak=self.hub.current_peak_dynamic,
            threshold_start=self.hub.threshold.start / 100
        )

    @property
    def above_stopthreshold(self) -> bool:
        return self._core._above_stop_threshold(
            predicted_energy=self.hub.prediction.predictedenergy,
            current_peak=self.hub.current_peak_dynamic,
            threshold_stop=self.hub.threshold.stop / 100
        )

    def _get_status_charging(self) -> ChargeControllerStates:
        if not self.hub.power_canary.alive:
            return ChargeControllerStates.Stop
        if all([
            self.above_stopthreshold,
            self.hub.sensors.totalhourlyenergy.value > 0,
            not self.hub.is_free_charge
        ]):
            return ChargeControllerStates.Stop
        return ChargeControllerStates.Start

    def _get_status_connected(self, charger_state=None) -> ChargeControllerStates:
        if charger_state is not None and self.hub.sensors.carpowersensor.value < 1 and self._is_done(charger_state):
            ret = ChargeControllerStates.Done
        else:
            if all([
                any([
                    (self.below_startthreshold and self.hub.sensors.totalhourlyenergy.value != 0),
                    self.hub.is_free_charge
                ]),
                not defer_start(self.hub.hours.non_hours)
            ]):
                ret = ChargeControllerStates.Start
            else:
                ret = ChargeControllerStates.Stop
        return ret

