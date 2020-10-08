from typing import List

from .AbstractMarketScenario import AbstractMarketScenario
from .Clock import Clock
from .abstract import AbstractMarketMaker, AbstractInvestor


class SynchronousMarketScenario(AbstractMarketScenario):

    def __init__(self, clock=Clock()):
        super().__init__(clock)

    def register_market_makers(self, *market_makers: AbstractMarketMaker) -> List[AbstractMarketMaker]:
        self.market_makers += list(market_makers)
        return list(market_makers)

    def register_investors(self, *investors: AbstractInvestor) -> List[AbstractInvestor]:
        for investor in investors:
            self.try_associate_market_makers(investor)

        self.investors += list(investors)

        return list(investors)

    def tick(self, seconds: int = 1):
        for investor in self.investors:
            investor.tick(self.clock.tick(seconds))

    def identify_investors(self):
        return [inv.get_qname() for inv in self.investors]
