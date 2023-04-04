from dataclasses import dataclass

from custom_components.peaqev.peaqservice.hub.models.hub_options import HubOptions
from custom_components.peaqev.peaqservice.hub.sensors.ihub_sensors import IHubSensors


@dataclass
class HubSensorsLite(IHubSensors):
    def setup(
            self,
            state_machine,
            options: HubOptions,
            domain: str,
            chargerobject: any):
        super().setup_base(state_machine=state_machine, options=options, domain=domain, chargerobject=chargerobject)