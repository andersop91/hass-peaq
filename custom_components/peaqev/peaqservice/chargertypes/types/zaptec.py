import logging

from homeassistant.core import HomeAssistant
from peaqevcore.hub.hub_options import HubOptions
from peaqevcore.models.chargecontroller_states import ChargeControllerStates
from peaqevcore.models.chargertype.calltype import CallType
from peaqevcore.models.chargertype.servicecalls_dto import ServiceCallsDTO
from peaqevcore.models.chargertype.servicecalls_options import ServiceCallsOptions
from peaqevcore.services.chargertype.chargertype_base import ChargerBase

import custom_components.peaqev.peaqservice.chargertypes.entitieshelper as helper

_LOGGER = logging.getLogger(__name__)

# docs: https://github.com/custom-components/zaptec


class Zaptec(ChargerBase):
    def __init__(self, hass: HomeAssistant, huboptions: HubOptions, auth_required: bool = False):
        self._hass = hass
        self._chargerid = huboptions.charger.chargerid
        self.entities.imported_entityendings = self.entity_endings
        self._auth_required = auth_required
        self.options.powerswitch_controls_charging = True

        self.chargerstates[ChargeControllerStates.Idle] = ["disconnected"]
        self.chargerstates[ChargeControllerStates.Connected] = ["waiting"]
        self.chargerstates[ChargeControllerStates.Charging] = ["charging"]
        self.chargerstates[ChargeControllerStates.Done] = ["charge_done"]

        try:
            entitiesobj = helper.set_entitiesmodel(
                hass=self._hass,
                domain=self.domain_name,
                entity_endings=self.entity_endings,
                entity_schema=self.entities.entityschema
            )
            self.entities.imported_entities = entitiesobj.imported_entities
            self.entities.entityschema = entitiesobj.entityschema
        except:
            _LOGGER.debug(f"Could not get a proper entityschema for {self.domain_name}.")

        self.set_sensors()
        self._set_servicecalls(
            domain=self.domain_name,
            model=ServiceCallsDTO(
                on=self.call_on,
                off=self.call_off,
                resume=self.call_resume,
                pause=self.call_pause
            ),
            options=self.servicecalls_options
        )

    @property
    def domain_name(self) -> str:
        """declare the domain name as stated in HA"""
        return "zaptec"

    @property
    def entity_endings(self) -> list:
        """declare a list of strings with sensor-endings to help peaqev find the correct sensor-schema."""
        return ["_switch", ""]

    @property
    def native_chargerstates(self) -> list:
        """declare a list of the native-charger states available for the type."""
        return [
            "unknown",
            "charging",
            "disconnected",
            "waiting",
            "charge_done"
        ]

    @property
    def call_on(self) -> CallType:
        return CallType("start_charging", {"charger_id": self._chargerid})

    @property
    def call_off(self) -> CallType:
        return CallType("stop_charging", {"charger_id": self._chargerid})

    @property
    def call_resume(self) -> CallType:
        return CallType("resume_charging", {"charger_id": self._chargerid})

    @property
    def call_pause(self) -> CallType:
        return CallType("stop_pause_charging", {"charger_id": self._chargerid})

    @property
    def call_update_current(self) -> CallType:
        raise NotImplementedError

    @property
    def servicecalls_options(self) -> ServiceCallsOptions:
        return ServiceCallsOptions(
                allowupdatecurrent=False,
                update_current_on_termination=False,
                switch_controls_charger=False
            )

    def set_sensors(self):
        try:
            self.entities.chargerentity = f"sensor.zaptec_{self.entities.entityschema}"
            self.entities.powermeter = f"{self.entities.chargerentity}|total_charge_power"
            self.options.powermeter_factor = 1
            self.entities.powerswitch = f"switch.zaptec_{self.entities.entityschema}_switch"
            _LOGGER.debug("Sensors for Zaptec have been set up.")
        except Exception as e:
            _LOGGER.exception(f"Could not set needed sensors for Zaptec. {e}")

    def _validate_sensor(self, sensor: str) -> bool:
        ret = self._hass.states.get(sensor)
        if ret is None:
            return False
        elif ret.state == "Null":
            return False
        return True