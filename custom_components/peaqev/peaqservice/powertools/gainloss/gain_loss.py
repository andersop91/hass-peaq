import logging

from peaqevcore.models.locale.enums.time_periods import TimePeriods

from custom_components.peaqev.peaqservice.powertools.gainloss.const import *
from custom_components.peaqev.peaqservice.powertools.gainloss.igain_loss import \
    IGainLoss

_LOGGER = logging.getLogger(__name__)


class GainLoss(IGainLoss):
    def __init__(self, hub):
        super().__init__()
        self._hub = hub
        self._hub.observer.add("monthly average price changed", self._update_monthly_average)
        self._hub.observer.add("daily average price changed", self._update_daily_average)

    async def async_get_consumption(self, time_period: TimePeriods) -> float:
        try:
            consumption = self._hub.state_machine.states.get(
                await self.async_get_entity(time_period, CONSUMPTION)
            )
            return float(consumption.state)
        except AttributeError:
            return 0.0

    async def async_get_cost(self, time_period: TimePeriods) -> float:
        try:
            cost = self._hub.state_machine.states.get(await self.async_get_entity(time_period, COST))
            return float(cost.state)
        except AttributeError:
            return 0.0


class GainLossTest(IGainLoss):
    def __init__(self, mock_states = None):
        self._mock_states = mock_states
        super().__init__()

    async def async_get_consumption(self, time_period: TimePeriods) -> float:
        try:
            consumption = self._mock_states.get(
                await self.async_get_entity(time_period, CONSUMPTION)
            )
            return float(consumption)
        except AttributeError:
            return 0.0

    async def async_get_cost(self, time_period: TimePeriods) -> float:
        try:
            cost = self._mock_states.get(await self.async_get_entity(time_period, COST))
            return float(cost)
        except AttributeError:
            return 0.0