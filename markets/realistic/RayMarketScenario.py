from typing import List

from .AbstractMarketScenario import AbstractMarketScenario
from .AbstractMarketMaker import AbstractMarketMaker
from .AbstractInvestor import AbstractInvestor
from .AsyncInvestor import AsyncInvestor
from .AsyncMarketMaker import AsyncMarketMaker


class RayMarketScenario(AbstractMarketScenario):

    def __init__(self):
        self.investors: List[AbstractInvestor] = []
        self.market_makers: List[AbstractMarketMaker] = []

    def register_investors(self, *investors):
        investors = [AsyncInvestor(investor) for investor in investors]
        self.investors += investors
        return investors

    def register_market_makers(self, *market_makers: AbstractMarketMaker) -> List[AbstractMarketMaker]:
        market_makers = [AsyncMarketMaker(market_maker) for market_maker in market_makers]
        self.market_makers += market_makers
        return market_makers

    def tick(self):
        for investor in self.investors:
            investor.tick()

    def identify_investors(self):
        return [inv.identify()
                for inv in self.investors]
