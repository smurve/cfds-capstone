from typing import List

from .AbstractMarketScenario import AbstractMarketScenario
from .AbstractMarketMaker import AbstractMarketMaker
from .AbstractInvestor import AbstractInvestor


class SynchronousMarketScenario(AbstractMarketScenario):

    def register_market_makers(self, *market_makers: AbstractMarketMaker) -> List[AbstractMarketMaker]:
        self.market_makers += list(market_makers)
        return list(market_makers)

    def __init__(self):
        self.investors: List[AbstractInvestor] = []
        self.market_makers: List[AbstractMarketMaker] = []

    def register_investors(self, *investors: AbstractInvestor) -> List[AbstractInvestor]:
        self.investors += list(investors)
        return list(investors)

    def tick(self):
        for investor in self.investors:
            investor.tick()

    def identify_investors(self):
        return [inv.identify() for inv in self.investors]
