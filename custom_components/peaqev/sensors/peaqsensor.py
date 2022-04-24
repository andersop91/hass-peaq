from custom_components.peaqev.sensors.sensorbase import SensorBase
from custom_components.peaqev.peaqservice.util.constants import CHARGERCONTROLLER

class PeaqSensor(SensorBase):
    def __init__(self, hub):
        name = f"{hub.hubname} {CHARGERCONTROLLER}"
        super().__init__(hub, name)

        self._attr_name = name
        self._state = self._hub.chargecontroller.status.name
        self._nonhours = None
        self._cautionhours = None

    @property
    def state(self):
        return self._hub.chargecontroller.status.name

    @property
    def icon(self) -> str:
        return "mdi:gate-xor"

    def update(self) -> None:
        self._state = self._hub.chargecontroller.status.name
        self._nonhours = self._hub.hours.non_hours
        self._cautionhours = self._hub.hours.caution_hours

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "non_hours": self._nonhours,
            "caution_hours": self._cautionhours,
            #current_hour state
            #"price aware?
            #"max money",
        }